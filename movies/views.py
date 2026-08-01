from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Q

from .models import Movie
from .serializers import MovieListSerializer, MovieDetailSerializer


class MovieListView(APIView):
    """
    GET /api/movies/
    Returns all movies with optional filters:
      ?search=    — title / plot / actor keyword search
      ?universe=  — e.g. MCU, Sony / Spider-Man
      ?phase=     — MCU phase (Phase 1 … Phase 5, Pre-MCU, etc.)
      ?genre=     — genre keyword
      ?type=      — movie | series
      ?canon=     — true | false  (is_mcu_canon)
      ?year_from= — minimum year
      ?year_to=   — maximum year
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Movie.objects.all()

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(plot__icontains=search) |
                Q(actors__icontains=search) |
                Q(tmdb_keywords__icontains=search) |
                Q(genre__icontains=search)
            )

        universe = request.query_params.get('universe', '').strip()
        if universe:
            qs = qs.filter(universe__icontains=universe)

        phase = request.query_params.get('phase', '').strip()
        if phase:
            qs = qs.filter(mcu_phase__icontains=phase)

        genre = request.query_params.get('genre', '').strip()
        if genre:
            qs = qs.filter(genre__icontains=genre)

        media_type = request.query_params.get('type', '').strip()
        if media_type:
            qs = qs.filter(type__iexact=media_type)

        canon = request.query_params.get('canon', '').strip().lower()
        if canon in ('true', '1'):
            qs = qs.filter(is_mcu_canon=True)
        elif canon in ('false', '0'):
            qs = qs.filter(is_mcu_canon=False)

        year_from = request.query_params.get('year_from', '').strip()
        if year_from.isdigit():
            qs = qs.filter(year__gte=int(year_from))

        year_to = request.query_params.get('year_to', '').strip()
        if year_to.isdigit():
            qs = qs.filter(year__lte=int(year_to))

        serializer = MovieListSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class MovieDetailView(APIView):
    """
    GET /api/movies/<id>/
    Returns full movie details including cast.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            movie = Movie.objects.prefetch_related('cast_members').get(pk=pk)
        except Movie.DoesNotExist:
            return Response({'error': 'Movie not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MovieDetailSerializer(movie)
        return Response(serializer.data)


class UniverseListView(APIView):
    """GET /api/movies/universes/ — unique universe values for filter dropdowns."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        universes = (
            Movie.objects.exclude(universe__isnull=True)
            .exclude(universe='')
            .values_list('universe', flat=True)
            .distinct()
            .order_by('universe')
        )
        return Response(list(universes))


class PhaseListView(APIView):
    """GET /api/movies/phases/ — unique MCU phase values for filter dropdowns."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        phases = (
            Movie.objects.exclude(mcu_phase__isnull=True)
            .exclude(mcu_phase='')
            .values_list('mcu_phase', flat=True)
            .distinct()
            .order_by('mcu_phase')
        )
        return Response(list(phases))
