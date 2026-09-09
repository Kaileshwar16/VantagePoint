"""Analysis views."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from api.models import Company
from .engine import analyze_company, analyze_all_companies


@api_view(['POST'])
def run_analysis(request, company_id):
    """Run analysis for a specific company."""
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        results = analyze_company(company_id)
        return Response({
            'company': company.name,
            'results': results,
            'message': f'Analysis complete. Found {results["patterns"]} patterns and generated {results["insights"]} insights.'
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('Analysis failed')
        return Response({'error': 'Analysis failed. Check server logs.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def run_all_analysis(request):
    """Run analysis for all tracked companies."""
    try:
        results = analyze_all_companies()
        return Response({
            'results': results,
            'message': f'Analysis complete for {len(results)} companies.'
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('Analysis failed')
        return Response({'error': 'Analysis failed. Check server logs.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
