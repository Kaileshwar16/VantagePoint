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
    results = {'errors': {}}
    steps = {
        'velocity_alerts': lambda: len(detect_velocity_alerts(company)),
        'anomalies': lambda: len(detect_anomalies(company)),
        'compound_signals': lambda: len(detect_compound_signals(company)),
        'battlecard_updated': lambda: update_battlecard(company),
        'dead_reckoning': lambda: run_dead_reckoning(company) is not None,
    }
    for name, operation in steps.items():
        try:
            results[name] = operation()
        except Exception:
            logger.exception('Analysis step failed: %s', name)
            results['errors'][name] = 'Step failed; check server logs.'
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
        recent = DataPoint.objects.filter(company=company, is_verified=True, category=cat,
                                         published_at__gte=now - timedelta(days=30)).count()
        prev = DataPoint.objects.filter(company=company, is_verified=True, category=cat,
                                       published_at__gte=now - timedelta(days=60),
                                       published_at__lt=now - timedelta(days=30)).count()
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
        cnt = (DataPoint.objects.filter(company=company, is_verified=True, published_at__gte=start, published_at__lt=end).count() +
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
    recent_dps = list(DataPoint.objects.filter(company=company, is_verified=True, published_at__gte=now - window))

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
                    recommendation=f'This compound signal is backed by {total_signals} matching records within a 14-day window (not necessarily independent sources). Heuristic score: {confidence*100:.0f}%.',
                    priority='high' if severity in ['high', 'critical'] else 'medium',
                    predicted_timeline='60-90 days',
                    probability=confidence,
                    metadata={'compound_signal_id': cs.id, 'signal_count': total_signals, 'methodology': 'compound-review-v1'},
                )
                compounds.append(cs)

    return compounds


# ========================================================================
# BATTLECARD AUTO-UPDATE
# ========================================================================
def update_battlecard(company):
    """Auto-update the competitive battlecard from latest signals.

    Generates meaningful strengths/weaknesses from signal categories,
    not just positive/negative headline dumps.
    """
    now = timezone.now()
    bc, created = Battlecard.objects.get_or_create(company=company)

    recent_dps = DataPoint.objects.filter(company=company, is_verified=True, published_at__gte=now - timedelta(days=60))
    recent_signals = Signal.objects.filter(company=company, captured_at__gte=now - timedelta(days=60))

    # ── Recent moves (top 5 most recent, skip garbage titles) ──────
    recent_moves = []
    for dp in recent_dps.order_by('-published_at')[:10]:
        title = dp.title.strip()
        # Skip garbage HTML artifacts
        if len(title) < 15 or title.lower() in ['skip to content', 'skip to main']:
            continue
        recent_moves.append({
            'title': title[:120],
            'category': dp.category,
            'date': dp.published_at.strftime('%Y-%m-%d') if dp.published_at else None,
            'source_url': dp.source_url,
        })
        if len(recent_moves) >= 5:
            break
    bc.recent_moves = recent_moves

    # ── Trajectory ─────────────────────────────────────────────────
    recent_30 = recent_dps.filter(published_at__gte=now - timedelta(days=30)).count()
    prev_30 = recent_dps.filter(published_at__lt=now - timedelta(days=30)).count()
    if recent_30 > prev_30 * 1.3:
        bc.current_trajectory = 'growing'
    elif recent_30 < prev_30 * 0.7:
        bc.current_trajectory = 'declining'
    else:
        bc.current_trajectory = 'stable'

    # ── Strengths: real competitive advantages from signal categories ──
    strengths = []

    # Product launches/tech innovations = competitive strength
    product_dps = recent_dps.filter(category__in=['product_launch', 'technology'])
    if product_dps.exists():
        count = product_dps.count()
        latest = product_dps.order_by('-published_at').first()
        strengths.append(f'Active product development: {count} product/tech signals in 60 days. Latest: {latest.title[:80]}')

    # Partnerships = ecosystem strength
    partner_dps = recent_dps.filter(category='partnership')
    if partner_dps.exists():
        strengths.append(f'Building ecosystem: {partner_dps.count()} partnership signal(s) — {partner_dps.first().title[:80]}')

    # Expansion = growth strength
    expansion_dps = recent_dps.filter(category='expansion')
    if expansion_dps.exists():
        strengths.append(f'Market expansion: {expansion_dps.count()} expansion signal(s)')

    # Funding = financial strength
    funding_dps = recent_dps.filter(category='funding')
    if funding_dps.exists():
        strengths.append(f'Recent funding activity: {funding_dps.count()} funding signal(s)')

    # Hiring = growth capacity
    hiring_signals = recent_signals.filter(signal_type='job_posting')
    if hiring_signals.count() > 3:
        strengths.append(f'Aggressive hiring: {hiring_signals.count()} job postings in 60 days')

    bc.strengths = strengths[:5]

    # ── Weaknesses: real business risks ────────────────────────────
    weaknesses = []

    # Legal issues
    legal_dps = recent_dps.filter(category='legal')
    if legal_dps.exists():
        weaknesses.append(f'Legal risk: {legal_dps.count()} legal signal(s) — {legal_dps.first().title[:80]}')

    # Negative sentiment articles with business impact
    neg_dps = recent_dps.filter(sentiment='negative').exclude(category='news')
    for dp in neg_dps[:3]:
        if dp.category in ['leadership', 'pricing_change']:
            weaknesses.append(f'{dp.get_category_display() if hasattr(dp, "get_category_display") else dp.category}: {dp.title[:80]}')

    # Declining trajectory
    if bc.current_trajectory == 'declining':
        weaknesses.append('Declining activity trend — fewer signals than previous period')

    # No product signals = potential stagnation
    if not product_dps.exists():
        weaknesses.append('Coverage gap: no product reports collected in 60 days; business activity is unknown.')

    bc.weaknesses = weaknesses[:5]

    # ── Signal summary ─────────────────────────────────────────────
    sig_counts = dict(recent_signals.values_list('signal_type').annotate(c=Count('id')).values_list('signal_type', 'c'))
    summary_parts = []
    for stype, count in sig_counts.items():
        summary_parts.append(f'{count} {stype.replace("_"," ")} signals')
    bc.signal_summary = f'Last 60 days: {", ".join(summary_parts)}.' if summary_parts else 'No recent signals.'

    # ── Threat assessment ──────────────────────────────────────────
    total_activity = recent_30 + recent_signals.filter(captured_at__gte=now - timedelta(days=30)).count()
    if total_activity > 20:
        bc.threat_assessment = f'HIGH OBSERVED ACTIVITY: {company.name} is extremely active with {total_activity} signals in 30 days.'
    elif total_activity > 10:
        bc.threat_assessment = f'MODERATE OBSERVED ACTIVITY: {company.name} has notable activity ({total_activity} signals in 30 days).'
    else:
        bc.threat_assessment = f'LOW OBSERVED ACTIVITY: {company.name} shows minimal activity ({total_activity} signals in 30 days).'

    bc.auto_update_count += 1
    bc.save()
    return True


# ========================================================================
# DEAD RECKONING — Forward projection (data-driven, real constants)
# ========================================================================

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
    Actively ignores amounts that are valuations (e.g. '$10B Valuation').
    Returns amount in millions, or 0 if unparseable.
    """
    import re
    text_lower = text.lower()

    amounts = []
    # Find all dollar amounts with optional B/M suffix
    for match in re.finditer(r'\$\s*([\d,]+(?:\.\d+)?)\s*(b|m|billion|million|mn)?\b', text_lower):
        val_str = match.group(1).replace(',', '')
        suffix = match.group(2)
        try:
            val = float(val_str)
        except ValueError:
            continue

        # Check context after match to see if it's a valuation
        start, end = match.span()
        context_after = text_lower[end:end+20]
        if 'valuation' in context_after or 'valued' in context_after or 'appraised' in context_after:
            continue  # Skip valuations

        if suffix in ['b', 'billion']:
            amounts.append(val * 1000)
        elif suffix in ['m', 'million', 'mn']:
            amounts.append(val)
        else:
            # no suffix, check if raw dollars are large enough
            if val >= 1_000_000:
                amounts.append(val / 1_000_000)
            elif val >= 1:
                amounts.append(val / 1_000_000)  # Unsuffixed amounts are dollars

    if amounts:
        return amounts[0]  # Return first valid funding amount found
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
    """Record observed activity without manufacturing business metrics or forecasts."""
    now = timezone.now()
    dps = DataPoint.objects.filter(company=company, is_verified=True).exclude(source_url='')
    jobs = Signal.objects.filter(company=company, signal_type='job_posting', captured_at__gte=now - timedelta(days=30)).exclude(source_url='')
    products = dps.filter(category='product_launch', published_at__gte=now - timedelta(days=90)).count()
    expansions = dps.filter(category='expansion', published_at__gte=now - timedelta(days=180)).count()
    return DeadReckoning.objects.create(
        company=company, current_geo_markets=0,
        hiring_velocity=jobs.values('source_url', 'title').distinct().count(),
        product_velocity=products, expansion_velocity=expansions * 2,
        confidence=0,
        projection_narrative=(f'{company.name}: observed activity only. '
            f'{products} verified product reports in 90 days; {expansions} verified expansion reports in 180 days. '
            'Reports are not unique products, markets, completed hires, or revenue. '
            'Financial and headcount forecasts are unavailable until sourced inputs and a validated forecasting model exist.'),
        key_assumptions=['methodology:observations-v1', 'Job counts use collection dates, not posting dates.',
            'Product velocity counts verified reports per quarter; expansion velocity annualizes verified reports.'],
        risk_factors=['Missing coverage is not evidence of inactivity.',
            'No calibrated forecast probability is available.', 'Company profile values require independent source verification.'],
    )


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

        for dp in DataPoint.objects.filter(company=company, is_verified=True, published_at__gte=since).order_by('published_at'):
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
