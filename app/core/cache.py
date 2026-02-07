"""
cachetools 不支持异步

"""

from aiocache import cached,caches
import httpx
import logging
logger = logging.getLogger(__name__)

@cached(ttl=60 * 60)
async def get_external_solar_data():
    """ solar指数
    """
    url = "https://services.swpc.noaa.gov/products/noaa-scales.json"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            data = response.json()
            current_solar = data['0']
            return current_solar['R']['Scale']
        except Exception as e:
            logger.exception(e)
            return 0


async def check_cache_status():
    """ 查看cache状态
    """
    cache = caches.get("default")
    logger.info(f'cache status :{cache}')