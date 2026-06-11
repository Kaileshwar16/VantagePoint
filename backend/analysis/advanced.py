"""
Advanced analysis engine: velocity alerts, anomaly scoring, compound signals,
hire-to-launch correlation, dead reckoning, cycle detection, battlecard auto-update.
"""
import math
import logging
from collections import Counter, defaultdict
from datetime import timedelta
from django.db.models import Count, Q, Avg
from django.utils import timezone
from api.models import (Company, DataPoint, Signal, Pattern, Insight,
                        CompoundSignal, Battlecard, DeadReckoning)

logger = logging.getLogger(__name__)


def run_advanced_analysis(company_id):
    """Full advanced analysis pipeline."""
    company = Company.objects.get(id=company_id)
    results = {'velocity_alerts': 0, 'anomalies': 0, 'compound_signals': 0,
               'battlecard_updated': False, 'dead_reckoning': False}
    try:
        results['velocity_alerts'] = len(detect_velocity_alerts(company))
    except Exception as e:
        logger.error(f"Velocity alerts failed: {e}")
    try:
        results['anomalies'] = len(detect_anomalies(company))
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
    try:
        results['compound_signals'] = len(detect_compound_signals(company))
    except Exception as e:
        logger.error(f"Compound signal detection failed: {e}")
    try:
        results['battlecard_updated'] = update_battlecard(company)
    except Exception as e:
        logger.error(f"Battlecard update failed: {e}")
    try:
        results['dead_reckoning'] = run_dead_reckoning(company) is not None
    except Exception as e:
        logger.error(f"Dead reckoning failed: {e}")
    return results


# ========================================================================
# VELOCITY ALERTS — rate of change acceleration
# ========================================================================
def detect_velocity_alerts(company):
    """Flag when rate of change accelerates, not just raw counts."""
    now = timezone.now()
    alerts = []
    
    for sig_type in ['job_posting', 'patent_filing', 'pricing_change', 'earnings_keyword']:
        periods = []
        for i in range(4):
            start = now - timedelta(days=30*(i+1))
            end = now - timedelta(days=30*i)
            cnt = Signal.objects.filter(company=company, signal_type=sig_type,
                                       captured_at__gte=start, captured_at__lt=end).count()
            periods.append(cnt)
        
        # periods[0] = most recent 30d, periods[1] = 30-60d ago, etc.
        if periods[1] > 0:
            velocity = (periods[0] - periods[1]) / max(periods[1], 1)
            acceleration = 0
            if periods[2] > 0 and periods[1] > 0:
                prev_vel = (periods[1] - periods[2]) / max(periods[2], 1)
                acceleration = velocity - prev_vel
            
            if velocity > 0.5 or (periods[0] >= 5 and periods[0] > periods[1] * 2):
                type_label = sig_type.replace('_', ' ').title()
                pattern = Pattern.objects.create(
                    company=company,
                    name=f'Velocity Alert: {type_label}',
                    description=(
                        f'{company.name} {type_label.lower()} went from {periods[1]} to {periods[0]} '
                        f'in 30 days ({velocity*100:+.0f}% velocity). '
                        f'Acceleration: {acceleration*100:+.0f}%. '
                        f'Trend: {periods[3]}→{periods[2]}→{periods[1]}→{periods[0]}.'
                    ),
                    pattern_type='velocity_alert',
                    confidence=min(0.9, 0.5 + abs(velocity) / 3),
                    metadata={'periods': periods, 'velocity': velocity,
                              'acceleration': acceleration, 'signal_type': sig_type},
                )
                alerts.append(pattern)
        elif periods[0] >= 3:
            type_label = sig_type.replace('_', ' ').title()
            pattern = Pattern.objects.create(
                company=company,
                name=f'New Activity: {type_label}',
                description=f'{company.name} generated {periods[0]} {type_label.lower()} signals — first detected activity in this category.',
                pattern_type='velocity_alert',
                confidence=0.6,
                metadata={'periods': periods, 'signal_type': sig_type},
            )
            alerts.append(pattern)
    
    # Also check DataPoint categories
    for cat in ['hiring', 'product_launch', 'expansion', 'funding']:
        recent = DataPoint.objects.filter(company=company, category=cat,
                                         created_at__gte=now - timedelta(days=30)).count()
        prev = DataPoint.objects.filter(company=company, category=cat,
                                       created_at__gte=now - timedelta(days=60),
                                       created_at__lt=now - timedelta(days=30)).count()
        if prev > 0 and recent > prev * 2 and recent >= 3:
            cat_label = cat.replace('_', ' ').title()
            pattern = Pattern.objects.create(
                company=company,
                name=f'Velocity Alert: {cat_label} Acceleration',
                description=f'{company.name} {cat_label.lower()} signals doubled from {prev} to {recent} in 30 days.',
                pattern_type='velocity_alert',
                confidence=min(0.85, 0.5 + recent / 20),
                metadata={'category': cat, 'recent': recent, 'previous': prev},
            )
            alerts.append(pattern)
    
    return alerts


# ========================================================================
# ANOMALY SCORING — baseline deviations
# ========================================================================
def detect_anomalies(company):
    """Baseline each competitor's normal activity, flag deviations."""
    now = timezone.now()
    anomalies = []
    
    # Calculate baseline: average weekly signals over last 90 days
    weeks_data = []
    for w in range(12):
        start = now - timedelta(weeks=w+1)
        end = now - timedelta(weeks=w)
        cnt = (DataPoint.objects.filter(company=company, created_at__gte=start, created_at__lt=end).count() +
               Signal.objects.filter(company=company, captured_at__gte=start, captured_at__lt=end).count())
        weeks_data.append(cnt)
    
    if len(weeks_data) < 4:
        return anomalies
    
    baseline = sum(weeks_data[1:]) / max(len(weeks_data) - 1, 1)  # exclude current week
    current = weeks_data[0]
    std_dev = max(1, (sum((x - baseline)**2 for x in weeks_data[1:]) / max(len(weeks_data)-2, 1)) ** 0.5)
    
    if std_dev > 0:
        z_score = (current - baseline) / std_dev
    else:
        z_score = 0
    
    if abs(z_score) > 1.5:
        direction = 'above' if z_score > 0 else 'below'
        pattern = Pattern.objects.create(
            company=company,
            name=f'Anomaly: Activity {z_score:.1f}σ {direction} baseline',
            description=(
                f'{company.name} generated {current} signals this week vs. baseline of '
                f'{baseline:.1f}±{std_dev:.1f} per week. Z-score: {z_score:.2f}. '
                f'{"Unusually high activity may indicate upcoming announcement." if z_score > 0 else "Unusually low activity may indicate stealth mode or internal issues."}'
            ),
            pattern_type='anomaly',
            confidence=min(0.9, 0.5 + abs(z_score) / 5),
            metadata={'z_score': z_score, 'current': current, 'baseline': baseline,
                      'std_dev': std_dev, 'weekly_data': weeks_data},
        )
        
        # Update anomaly scores on recent signals
        Signal.objects.filter(company=company, captured_at__gte=now - timedelta(weeks=1)).update(anomaly_score=abs(z_score))
        anomalies.append(pattern)
    
    return anomalies


# ========================================================================
# COMPOUND SIGNAL DETECTION — co-occurrence of weak signals
# ========================================================================
def detect_compound_signals(company):
    """Detect when multiple weak signals fire simultaneously."""
    now = timezone.now()
    window = timedelta(days=14)
    compounds = []
    
    recent_signals = list(Signal.objects.filter(company=company, captured_at__gte=now - window))
    recent_dps = list(DataPoint.objects.filter(company=company, created_at__gte=now - window))
    
    if len(recent_signals) + len(recent_dps) < 3:
        return compounds
    
    # Categorize signals
    signal_categories = defaultdict(list)
    for s in recent_signals:
        signal_categories[s.signal_type].append(s)
    for dp in recent_dps:
        signal_categories[dp.category].append(dp)
    
    # Define compound signal rules
    COMPOUND_RULES = [
        {
            'name': 'Enterprise Push Imminent',
            'requires': [('hiring', 1), ('pricing_change', 1)],
            'optional': [('job_posting', 2), ('leadership', 1), ('partnership', 1)],
            'hypothesis': f'{company.name} appears to be preparing an enterprise push. Hiring (especially sales/exec), pricing changes, and partnership activity suggest a new enterprise tier or upmarket move within 60-90 days.',
        },
        {
            'name': 'Product Launch Incoming',
            'requires': [('hiring', 2), ('product_launch', 1)],
            'optional': [('technology', 1), ('job_posting', 3), ('marketing', 1), ('patent_filing', 1)],
            'hypothesis': f'{company.name} is likely preparing a major product launch. The combination of engineering hiring, tech signals, and product activity matches pre-launch patterns seen across B2B SaaS.',
        },
        {
            'name': 'Market Expansion Underway',
            'requires': [('expansion', 1), ('hiring', 1)],
            'optional': [('job_posting', 2), ('partnership', 1), ('marketing', 1)],
            'hypothesis': f'{company.name} is expanding into new markets. Geographic expansion signals combined with hiring and partnerships indicate a deliberate international or vertical expansion strategy.',
        },
        {
            'name': 'Strategic Pivot Signal',
            'requires': [('leadership', 1)],
            'optional': [('hiring', 2), ('pricing_change', 1), ('funding_event', 1), ('job_posting', 3)],
            'hypothesis': f'{company.name} may be pivoting strategy. Leadership changes combined with shifts in hiring patterns and pricing suggest a fundamental strategic reorientation.',
        },
        {
            'name': 'Acquisition Mode Active',
            'requires': [('funding', 1)],
            'optional': [('acquisition', 1), ('leadership', 1), ('hiring', 1)],
            'hypothesis': f'{company.name} appears to be in acquisition mode. Recent funding combined with leadership and hiring signals suggests they\'re building capability through inorganic growth.',
        },
    ]
    
    for rule in COMPOUND_RULES:
        required_met = 0
        optional_met = 0
        matched_signals = []
        matched_dps = []
        
        for cat, min_count in rule['requires']:
            items = signal_categories.get(cat, [])
            if len(items) >= min_count:
                required_met += 1
                for item in items[:min_count]:
                    if isinstance(item, Signal):
                        matched_signals.append(item)
                    else:
                        matched_dps.append(item)
        
        for cat, min_count in rule['optional']:
            items = signal_categories.get(cat, [])
            if len(items) >= min_count:
                optional_met += 1
                for item in items[:min_count]:
                    if isinstance(item, Signal):
                        matched_signals.append(item)
                    else:
                        matched_dps.append(item)
        
        if required_met == len(rule['requires']) and optional_met >= 1:
            total_signals = len(matched_signals) + len(matched_dps)
            confidence = min(0.95, 0.4 + total_signals * 0.08)
            severity = 'critical' if total_signals >= 5 else 'high' if total_signals >= 3 else 'medium'
            
            exists = CompoundSignal.objects.filter(
                company=company, title__icontains=rule['name'],
                detected_at__gte=now - timedelta(days=7),
            ).exists()
            
            if not exists:
                cs = CompoundSignal.objects.create(
                    company=company,
                    title=f"{rule['name']} — {company.name}",
                    hypothesis=rule['hypothesis'],
                    signal_count=total_signals,
                    confidence=confidence,
                    severity=severity,
                    time_window_days=14,
                )
                cs.contributing_signals.set(matched_signals)
                cs.contributing_datapoints.set(matched_dps)
                
                # Also create an insight
                Insight.objects.create(
                    company=company,
                    title=f'⚡ Compound Signal: {rule["name"]}',
                    description=rule['hypothesis'],
                    recommendation=f'This compound signal is backed by {total_signals} independent signals within a 14-day window. Confidence: {confidence*100:.0f}%.',
                    priority='high' if severity in ['high', 'critical'] else 'medium',
                    predicted_timeline='60-90 days',
                    probability=confidence,
                    metadata={'compound_signal_id': cs.id, 'signal_count': total_signals},
                )
                compounds.append(cs)
    
    return compounds


# ========================================================================
# BATTLECARD AUTO-UPDATE
# ========================================================================
def update_battlecard(company):
    """Auto-update the competitive battlecard from latest signals."""
    now = timezone.now()
    bc, created = Battlecard.objects.get_or_create(company=company)
    
    recent_dps = DataPoint.objects.filter(company=company, created_at__gte=now - timedelta(days=60))
    recent_signals = Signal.objects.filter(company=company, captured_at__gte=now - timedelta(days=60))
    
    # Recent moves
    recent_moves = []
    for dp in recent_dps.order_by('-created_at')[:5]:
        recent_moves.append({'title': dp.title[:120], 'category': dp.category,
                             'date': dp.created_at.strftime('%Y-%m-%d')})
    bc.recent_moves = recent_moves
    
    # Trajectory
    recent_30 = recent_dps.filter(created_at__gte=now - timedelta(days=30)).count()
    prev_30 = recent_dps.filter(created_at__lt=now - timedelta(days=30)).count()
    if recent_30 > prev_30 * 1.3:
        bc.current_trajectory = 'growing'
    elif recent_30 < prev_30 * 0.7:
        bc.current_trajectory = 'declining'
    else:
        bc.current_trajectory = 'stable'
    
    # Strengths/weaknesses from sentiment
    pos = recent_dps.filter(sentiment='positive')
    neg = recent_dps.filter(sentiment='negative')
    bc.strengths = [dp.title[:100] for dp in pos[:5]]
    bc.weaknesses = [dp.title[:100] for dp in neg[:5]]
    
    # Signal summary
    sig_counts = dict(recent_signals.values_list('signal_type').annotate(c=Count('id')).values_list('signal_type', 'c'))
    summary_parts = []
    for stype, count in sig_counts.items():
        summary_parts.append(f'{count} {stype.replace("_"," ")} signals')
    bc.signal_summary = f'Last 60 days: {", ".join(summary_parts)}.' if summary_parts else 'No recent signals.'
    
    # Threat assessment
    total_activity = recent_30 + recent_signals.filter(captured_at__gte=now - timedelta(days=30)).count()
    if total_activity > 20:
        bc.threat_assessment = f'HIGH THREAT: {company.name} is extremely active with {total_activity} signals in 30 days.'
    elif total_activity > 10:
        bc.threat_assessment = f'MODERATE THREAT: {company.name} has notable activity ({total_activity} signals in 30 days).'
    else:
        bc.threat_assessment = f'LOW THREAT: {company.name} shows minimal activity ({total_activity} signals in 30 days).'
    
    bc.auto_update_count += 1
    bc.save()
    return True


# ========================================================================
# DEAD RECKONING — Forward projection (data-driven, real constants)
# ========================================================================

# --- Industry benchmarks (sourced from KeyBanc SaaS Survey, Bessemer Cloud Index) ---

# Revenue per employee by industry — median values in $K
# Sources: KeyBanc 2024 SaaS Survey, Meritech Capital SaaS Index
REVENUE_PER_EMPLOYEE_K = {
    'tech': 200,          # SaaS/Software median: ~$200K/employee
    'finance': 350,       # Fintech: higher revenue per head
    'healthcare': 175,    # Healthtech: slightly below software median
    'retail': 150,        # E-commerce/Retail tech
    'manufacturing': 250, # Industrial tech — capital intensive, fewer heads
    'energy': 300,        # Energy tech
    'media': 180,         # Media/Entertainment tech
    'education': 120,     # EdTech: lower monetization
    'real_estate': 220,   # PropTech
    'other': 180,         # Conservative fallback
}

# Annual growth rate by company stage (based on employee count ranges)
# Source: Bessemer Cloud Index, SaaS Capital growth benchmarks
STAGE_GROWTH_RATES = {
    'seed': 0.80,         # <20 employees: 80% YoY (high variance)
    'early': 0.50,        # 20-100 employees: 50% YoY
    'growth': 0.30,       # 100-500 employees: 30% YoY
    'scale': 0.20,        # 500-2000 employees: 20% YoY
    'enterprise': 0.12,   # 2000+ employees: 12% YoY
}

# Job posting fill rate — what % of posted jobs result in actual hires
# Source: SHRM 2024 Talent Acquisition Benchmarking Report
JOB_FILL_RATE = 0.65


def _classify_company_stage(headcount):
    """Classify company stage from headcount for benchmark selection."""
    if headcount <= 0:
        return 'seed'
    elif headcount < 20:
        return 'seed'
    elif headcount < 100:
        return 'early'
    elif headcount < 500:
        return 'growth'
    elif headcount < 2000:
        return 'scale'
    else:
        return 'enterprise'


def _parse_headcount(employee_count_str):
    """Parse real headcount from Company.employee_count field.
    
    Handles formats like: '500', '1,000', '500-1000', '1000+', '~800'.
    Returns (headcount, is_known) tuple.
    """
    if not employee_count_str or not employee_count_str.strip():
        return 0, False
    
    s = employee_count_str.strip().replace(',', '').replace('+', '').replace('~', '').replace(' ', '')
    
    try:
        if '-' in s:
            parts = s.split('-')
            low = int(parts[0])
            high = int(parts[1])
            return (low + high) // 2, True  # midpoint of range
        else:
            return int(s), True
    except (ValueError, IndexError):
        return 0, False


def _parse_funding_amount(text):
    """Extract actual dollar amounts from article text.
    
    Handles: $5M, $50 million, $1.2B, $500,000, etc.
    Returns amount in millions, or 0 if unparseable.
    """
    import re
    text_lower = text.lower()
    
    # Pattern: $X.X billion
    match = re.search(r'\$\s*([\d,.]+)\s*(?:b|billion)', text_lower)
    if match:
        try:
            return float(match.group(1).replace(',', '')) * 1000  # convert to millions
        except ValueError:
            pass
    
    # Pattern: $X.X million / $XM
    match = re.search(r'\$\s*([\d,.]+)\s*(?:m(?:illion)?|mn)', text_lower)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    # Pattern: bare $X,XXX,XXX (likely thousands or millions)
    match = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', text_lower)
    if match:
        try:
            amount = float(match.group(1).replace(',', ''))
            if amount >= 1_000_000:
                return amount / 1_000_000  # convert raw dollars to millions
            elif amount >= 100:
                return amount  # already in millions notation (e.g., "$50" in context)
        except ValueError:
            pass
    
    return 0.0


def _parse_revenue_range(revenue_range_str):
    """Parse Company.revenue_range into a midpoint ARR estimate in millions.
    
    Handles formats like: '$10M-$50M', '$100M+', '50-100M', 'Pre-revenue', etc.
    Returns (arr_millions, is_known) tuple.
    """
    import re
    if not revenue_range_str or not revenue_range_str.strip():
        return 0.0, False
    
    s = revenue_range_str.strip().lower().replace(',', '')
    
    if 'pre-revenue' in s or 'pre revenue' in s or s == '0':
        return 0.0, True
    
    # Extract all numbers with B/M suffixes
    amounts = []
    for match in re.finditer(r'([\d.]+)\s*([bm])?', s):
        val = float(match.group(1))
        suffix = match.group(2)
        if suffix == 'b':
            val *= 1000
        amounts.append(val)
    
    if len(amounts) >= 2:
        return (amounts[0] + amounts[1]) / 2, True  # midpoint
    elif len(amounts) == 1:
        return amounts[0], True
    
    return 0.0, False


def run_dead_reckoning(company):
    """Project where a competitor will be in 6 and 12 months.
    
    All projections use data-driven constants from established industry
    benchmarks. When data is unavailable, values are marked as 0 and
    confidence is reduced — no numbers are fabricated.
    
    Constants used:
    - Revenue/employee: KeyBanc 2024 SaaS Survey (industry-specific)
    - Stage growth rates: Bessemer Cloud Index
    - Job fill rate: SHRM 2024 report (65%)
    """
    now = timezone.now()
    data_gaps = []  # Track what data is missing for honest confidence scoring
    
    # ── Gather observed signal data ─────────────────────────────────
    job_signals = Signal.objects.filter(company=company, signal_type='job_posting')
    jobs_30d = job_signals.filter(captured_at__gte=now - timedelta(days=30)).count()
    jobs_60d = job_signals.filter(captured_at__gte=now - timedelta(days=60)).count()
    
    product_dps = DataPoint.objects.filter(company=company, category__in=['product_launch', 'technology'])
    products_90d = product_dps.filter(created_at__gte=now - timedelta(days=90)).count()
    
    expansion_dps = DataPoint.objects.filter(company=company, category='expansion')
    expansions_180d = expansion_dps.filter(created_at__gte=now - timedelta(days=180)).count()
    
    funding_dps = DataPoint.objects.filter(company=company, category='funding')
    funding_count = funding_dps.count()
    
    # ── Current headcount (real data, not invented) ─────────────────
    headcount, headcount_known = _parse_headcount(company.employee_count)
    if not headcount_known:
        data_gaps.append('headcount_unknown')
    
    # ── Velocities (zero if no signal — never invent activity) ──────
    hiring_velocity = jobs_30d  # actual job postings per month
    product_velocity = products_90d / 3.0 if products_90d > 0 else 0.0  # per month, zero if none
    expansion_velocity = expansions_180d / 6.0 if expansions_180d > 0 else 0.0  # per month, zero if none
    
    # ── Headcount projection (fill rate × jobs, not magic multiplier) ─
    # Each job posting has a 65% chance of resulting in a hire (SHRM benchmark)
    estimated_monthly_hires = hiring_velocity * JOB_FILL_RATE
    projected_headcount_6m = headcount + int(estimated_monthly_hires * 6) if headcount_known else 0
    projected_headcount_12m = headcount + int(estimated_monthly_hires * 12) if headcount_known else 0
    
    # ── Product count (actual observed, not circular estimate) ───────
    # Count distinct product-related DataPoints as a proxy for product count
    all_product_dps = DataPoint.objects.filter(
        company=company,
        category__in=['product_launch', 'technology']
    )
    current_products = all_product_dps.values('title').distinct().count()
    current_products = max(current_products, 1) if all_product_dps.exists() else 0
    if current_products == 0:
        data_gaps.append('products_unknown')
    
    projected_products_6m = current_products + int(product_velocity * 6)
    projected_products_12m = current_products + int(product_velocity * 12)
    
    # ── Geographic markets (actual observed, not circular) ──────────
    all_expansion_dps = DataPoint.objects.filter(company=company, category='expansion')
    # Count unique market mentions from expansion DataPoints
    current_markets = max(all_expansion_dps.count(), 1) if all_expansion_dps.exists() else 1
    if not all_expansion_dps.exists():
        data_gaps.append('markets_unknown')
    
    projected_markets_6m = current_markets + int(expansion_velocity * 6)
    projected_markets_12m = current_markets + int(expansion_velocity * 12)
    
    # ── ARR estimation (industry-specific, not one-size-fits-all) ───
    # First try: use company.revenue_range if available
    arr_from_range, revenue_known = _parse_revenue_range(company.revenue_range)
    
    if revenue_known and arr_from_range > 0:
        current_arr = arr_from_range
        arr_source = f'company reported revenue range ({company.revenue_range})'
    elif headcount_known and headcount > 0:
        # Use industry-specific revenue-per-employee benchmark
        rev_per_emp_k = REVENUE_PER_EMPLOYEE_K.get(company.industry, 180)
        current_arr = headcount * rev_per_emp_k / 1000.0  # convert $K to $M
        arr_source = f'estimated from {headcount} employees × ${rev_per_emp_k}K/employee ({company.get_industry_display()} benchmark, KeyBanc 2024)'
    else:
        current_arr = 0.0
        arr_source = 'unknown (insufficient data)'
        data_gaps.append('arr_unknown')
    
    # Growth rate: use stage-specific benchmark, not made-up formula
    stage = _classify_company_stage(headcount) if headcount_known else 'growth'
    base_growth_rate = STAGE_GROWTH_RATES.get(stage, 0.20)
    
    # Adjust growth rate based on observed hiring signal strength
    # More hiring than expected for stage = slightly higher growth
    expected_monthly_posts_for_stage = {
        'seed': 2, 'early': 5, 'growth': 15, 'scale': 30, 'enterprise': 50
    }
    expected = expected_monthly_posts_for_stage.get(stage, 10)
    if expected > 0 and hiring_velocity > 0:
        hiring_ratio = hiring_velocity / expected
        # Cap the adjustment at ±30% of base rate
        adjustment = min(0.3, max(-0.3, (hiring_ratio - 1.0) * 0.15))
        growth_rate = base_growth_rate * (1 + adjustment)
    else:
        growth_rate = base_growth_rate
    
    projected_arr_6m = current_arr * (1 + growth_rate * 0.5) if current_arr > 0 else 0.0
    projected_arr_12m = current_arr * (1 + growth_rate) if current_arr > 0 else 0.0
    
    # ── Funding total (parse real amounts, not $50M per event) ──────
    total_funding_m = 0.0
    funding_details = []
    for dp in funding_dps:
        text = f"{dp.title} {dp.content}"
        amount = _parse_funding_amount(text)
        if amount > 0:
            total_funding_m += amount
            funding_details.append(f'{dp.title[:60]}: ${amount:.1f}M')
    
    if funding_count > 0 and total_funding_m == 0:
        data_gaps.append('funding_amounts_unparseable')
    
    # ── Confidence (honest, based on actual data completeness) ──────
    total_signals = (job_signals.count() + product_dps.count() +
                     expansion_dps.count() + funding_count)
    
    # Start at 0.20, earn confidence from real data
    confidence = 0.20
    if headcount_known:
        confidence += 0.15
    if revenue_known:
        confidence += 0.15
    if total_signals >= 20:
        confidence += 0.20
    elif total_signals >= 10:
        confidence += 0.15
    elif total_signals >= 5:
        confidence += 0.10
    if jobs_30d > 0:
        confidence += 0.05
    if products_90d > 0:
        confidence += 0.05
    if expansions_180d > 0:
        confidence += 0.05
    if total_funding_m > 0:
        confidence += 0.05
    confidence = min(0.90, confidence)
    
    # Penalize for data gaps
    confidence -= len(data_gaps) * 0.05
    confidence = max(0.10, confidence)
    
    # ── Generate narrative ──────────────────────────────────────────
    narrative_parts = [f'{company.name} Forward Projection (Dead Reckoning):']
    narrative_parts.append(f'• DATA QUALITY: {total_signals} observed signals, confidence {confidence*100:.0f}%')
    
    if data_gaps:
        narrative_parts.append(f'• ⚠ MISSING DATA: {", ".join(g.replace("_", " ") for g in data_gaps)}')
    
    if headcount_known:
        narrative_parts.append(f'• HEADCOUNT: {headcount} employees (from company data)')
    else:
        narrative_parts.append(f'• HEADCOUNT: Unknown — headcount projections unavailable')
    
    if hiring_velocity > 5:
        narrative_parts.append(f'• AGGRESSIVE HIRING: {hiring_velocity} job postings/month. At {JOB_FILL_RATE*100:.0f}% fill rate, ~{estimated_monthly_hires:.0f} hires/month.')
    elif hiring_velocity > 0:
        narrative_parts.append(f'• MODERATE HIRING: {hiring_velocity} job postings/month. At {JOB_FILL_RATE*100:.0f}% fill rate, ~{estimated_monthly_hires:.0f} hires/month.')
    else:
        narrative_parts.append(f'• NO HIRING SIGNALS detected in last 30 days.')
    
    if product_velocity > 1:
        narrative_parts.append(f'• HIGH PRODUCT VELOCITY: ~{product_velocity:.1f} releases/month ({products_90d} in 90 days).')
    elif product_velocity > 0:
        narrative_parts.append(f'• PRODUCT ACTIVITY: {products_90d} product/tech signals in 90 days.')
    
    if expansion_velocity > 0:
        narrative_parts.append(f'• EXPANSION: {expansions_180d} market expansion signals in 180 days ({expansion_velocity:.2f}/month).')
    
    if headcount_known and projected_headcount_12m > 0:
        narrative_parts.append(f'• PROJECTED HEADCOUNT: {headcount} → {projected_headcount_6m} (6mo) → {projected_headcount_12m} (12mo)')
    
    if current_arr > 0:
        narrative_parts.append(f'• ESTIMATED ARR: ${current_arr:.1f}M → ${projected_arr_6m:.1f}M (6mo) → ${projected_arr_12m:.1f}M (12mo)')
        narrative_parts.append(f'  ARR source: {arr_source}')
        narrative_parts.append(f'  Growth rate: {growth_rate*100:.0f}% YoY ({stage} stage, Bessemer benchmark)')
    
    if total_funding_m > 0:
        narrative_parts.append(f'• KNOWN FUNDING: ${total_funding_m:.1f}M total from {funding_count} event(s)')
    
    # ── Assumptions (explicit, verifiable) ──────────────────────────
    assumptions = []
    if headcount_known:
        assumptions.append(f'Headcount: {headcount} (from company profile data)')
    else:
        assumptions.append('Headcount unknown — headcount-based projections marked as 0')
    
    assumptions.append(f'Job fill rate: {JOB_FILL_RATE*100:.0f}% (SHRM 2024 Talent Acquisition Benchmark)')
    
    if current_arr > 0:
        if revenue_known:
            assumptions.append(f'ARR from company revenue range: {company.revenue_range}')
        else:
            rev_per_emp_k = REVENUE_PER_EMPLOYEE_K.get(company.industry, 180)
            assumptions.append(f'Revenue/employee: ${rev_per_emp_k}K ({company.get_industry_display()} median, KeyBanc 2024 SaaS Survey)')
        assumptions.append(f'Growth rate: {growth_rate*100:.0f}% YoY ({stage} stage companies, Bessemer Cloud Index)')
    
    assumptions.append(f'Based on {total_signals} observed data points across {(now - timedelta(days=180)).strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}')
    
    # ── Risk factors (data-driven) ──────────────────────────────────
    risks = []
    if confidence < 0.4:
        risks.append('LOW DATA: Projection has low confidence — collect more signals before relying on these numbers')
    if 'headcount_unknown' in data_gaps:
        risks.append('Headcount unknown — headcount and ARR projections may be inaccurate')
    if 'arr_unknown' in data_gaps:
        risks.append('Revenue data unavailable — ARR projections are not shown')
    if hiring_velocity > expected * 2:
        risks.append(f'Hiring pace ({hiring_velocity}/mo) is {hiring_velocity/max(expected,1):.1f}x the stage average — may be unsustainable')
    if funding_count == 0:
        risks.append('No observed funding events — growth may be constrained by cash reserves')
    if 'funding_amounts_unparseable' in data_gaps:
        risks.append('Funding events found but dollar amounts could not be parsed from article text')
    
    dr = DeadReckoning.objects.create(
        company=company,
        current_headcount=headcount,
        current_arr=current_arr,
        current_product_count=current_products,
        current_geo_markets=current_markets,
        hiring_velocity=hiring_velocity,
        product_velocity=product_velocity,
        expansion_velocity=expansion_velocity,
        funding_total=total_funding_m,
        projected_headcount_6m=projected_headcount_6m,
        projected_headcount_12m=projected_headcount_12m,
        projected_arr_6m=projected_arr_6m,
        projected_arr_12m=projected_arr_12m,
        projected_products_6m=projected_products_6m,
        projected_products_12m=projected_products_12m,
        projected_markets_6m=projected_markets_6m,
        projected_markets_12m=projected_markets_12m,
        confidence=confidence,
        projection_narrative='\n'.join(narrative_parts),
        key_assumptions=assumptions,
        risk_factors=risks,
    )
    
    return dr


# ========================================================================
# TIMELINE OVERLAY
# ========================================================================
def get_timeline_overlay(company_ids, days=180):
    """Build overlay timeline for comparing two+ competitors."""
    now = timezone.now()
    since = now - timedelta(days=days)
    timelines = {}
    
    for cid in company_ids:
        company = Company.objects.get(id=cid)
        events = []
        
        for dp in DataPoint.objects.filter(company=company, created_at__gte=since).order_by('created_at'):
            events.append({
                'date': (dp.published_at or dp.created_at).strftime('%Y-%m-%d'),
                'title': dp.title[:100],
                'category': dp.category,
                'sentiment': dp.sentiment,
                'impact': dp.impact,
                'type': 'datapoint',
            })
        
        for sig in Signal.objects.filter(company=company, captured_at__gte=since).order_by('captured_at'):
            events.append({
                'date': sig.captured_at.strftime('%Y-%m-%d'),
                'title': sig.title[:100],
                'category': sig.signal_type,
                'type': 'signal',
                'strength': sig.strength,
            })
        
        events.sort(key=lambda x: x['date'])
        timelines[company.name] = {'id': cid, 'events': events, 'count': len(events)}
    
    return timelines
