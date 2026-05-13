import logging

logger = logging.getLogger(__name__)

class MovieAPI:
    async def get_movie(self, movie_name: str):
        logger.info(f"Searching for movie: {movie_name}")
        return None
    
    async def get_trending(self, limit=10):
        return []
    
    async def get_top_rated(self, limit=10):
        return []

movie_api = MovieAPI()
