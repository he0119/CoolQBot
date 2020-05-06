#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author         : richardchien
@Date           : 2020-04-14 22:13:36
@LastEditors    : yanyongyu
@LastEditTime   : 2020-04-14 22:20:18
@Description    : None
@GitHub         : https://github.com/richardchien
"""
__author__ = "richardchien"

from typing import Optional, List, Any, Dict

import httpx
from aiocache import cached
from nonebot.log import logger

INDEX_API_URL = 'https://bangumi.bilibili.com/media/web_api/search/result'
TIMELINE_API_URL = 'http://bangumi.bilibili.com/web_api/timeline_v4'

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/75.0.3770.100 Safari/537.36'
}


@cached(ttl=5 * 60)
async def get_anime_list(year: int,
                         month: int) -> Optional[List[Dict[str, Any]]]:
    payload = {
        'season_version': -1,
        'area': -1,
        'is_finish': -1,
        'copyright': -1,
        'season_status': -1,
        'season_month': month,
        'pub_date': year,
        'style_id': -1,
        'order': 3,
        'st': 1,
        'sort': 0,
        'page': 1,
        'season_type': 1,
        'pagesize': 20
    }
    async with httpx.AsyncClient(headers=HEADER) as client:
        try:
            response = await client.get(INDEX_API_URL, params=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('code') != 0:
                return None
            return data['result']['data']
        except (httpx.HTTPError, KeyError) as e:
            logger.error(e)
            return None


@cached(ttl=5 * 60)
async def get_timeline_list() -> Optional[List[Dict[str, Any]]]:
    async with httpx.AsyncClient(headers=HEADER) as client:
        try:
            response = await client.get(TIMELINE_API_URL, headers=HEADER)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get('code') != 0:
                return None
            return payload['result'] or []
        except (httpx.HTTPError, KeyError) as e:
            logger.error(e)
            return None
