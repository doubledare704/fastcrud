from typing import TypeVar, Any, Union
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

FilterValue = Union[str, int, float, bool, datetime, Decimal, None]
FilterValueSequence = Union[
    list[FilterValue], tuple[FilterValue, ...], set[FilterValue]
]
FilterValueType = Union[FilterValue, FilterValueSequence, dict[str, FilterValue]]

ModelType = TypeVar("ModelType", bound=Any)

SelectSchemaType = TypeVar("SelectSchemaType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
UpdateSchemaInternalType = TypeVar("UpdateSchemaInternalType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)

GetMultiResponseDict = dict[str, Union[list[dict[str, Any]], int]]
GetMultiResponseModel = dict[str, Union[list[SelectSchemaType], int]]

UpsertMultiResponseDict = dict[str, list[dict[str, Any]]]
UpsertMultiResponseModel = dict[str, list[SelectSchemaType]]
