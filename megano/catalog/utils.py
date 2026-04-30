import json
import logging
from typing import Dict, Tuple, Union, Optional
from django.db.models import QuerySet, Q
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def extract_filters(request)-> Dict[str, Union[str, int, float, bool]]:
    """Извлекает фильтры из запроса"""
    filters = {}

    # JSON filter
    filter_json = request.query_params.get('filter')
    if filter_json:
        try:
            filters.update(json.loads(filter_json))
        except json.JSONDecodeError:
            pass

    # Nested filters
    nested_keys = ['name', 'minPrice', 'maxPrice', 'freeDelivery', 'available']
    for key in nested_keys:
        value = request.query_params.get(f'filter[{key}]')
        if value is not None and value != '':
            filters[key] = value

    return filters


def apply_search_filter(queryset: QuerySet, search_text: str) -> QuerySet:
    """Применяет поиск по тексту с игнорированием регистра и первой буквы"""
    if not search_text:
        return queryset

    search_lower = search_text.lower()
    q_objects = Q()

    # точное совпадение
    q_objects |= (
            Q(title__icontains=search_lower) |
            Q(description__icontains=search_lower) |
            Q(full_description__icontains=search_lower)
    )

    # без последней буквы
    if len(search_lower) > 1:
        without_last = search_lower[:-1]
        q_objects |= (
                Q(title__icontains=without_last) |
                Q(description__icontains=without_last) |
                Q(full_description__icontains=without_last)
        )

    # без первой буквы (Наушники наушники)
    if len(search_lower) > 2:
        without_first = search_lower[1:]
        q_objects |= (
                Q(title__icontains=without_first) |
                Q(description__icontains=without_first) |
                Q(full_description__icontains=without_first)
        )

    # по отдельным словам
    words = search_lower.split()
    if len(words) > 1:
        for word in words:
            if len(word) > 2:
                q_objects |= (
                        Q(title__icontains=word) |
                        Q(description__icontains=word) |
                        Q(full_description__icontains=word)
                )

    return queryset.filter(q_objects).distinct()


def apply_price_filter(
    queryset: QuerySet,
    min_price: Optional[Union[str, float, int]],
    max_price: Optional[Union[str, float, int]]
) -> QuerySet:
    """Применяет фильтр по цене"""
    if min_price:
        try:
            queryset = queryset.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            queryset = queryset.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass

    return queryset


def to_bool(value: Union[str, bool, int, None]) -> bool:
    """Конвертирует строку в булево значение"""
    if isinstance(value, str):
        return value.lower() == 'true'
    return bool(value)


def get_pagination_params(request)-> Tuple[int, int]:
    """Получает и валидирует параметры пагинации"""
    default_limit = 20
    max_limit = 100

    try:
        limit = int(request.query_params.get('limit', default_limit))
        current_page = int(request.query_params.get('currentPage', 1))

        # Валидация
        limit = max(1, min(limit, max_limit))
        current_page = max(1, current_page)

    except (ValueError, TypeError):
        limit = default_limit
        current_page = 1

    return limit, current_page