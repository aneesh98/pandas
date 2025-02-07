from datetime import datetime

import numpy as np
import pytest

import pandas as pd
from pandas import (
    DataFrame,
    Series,
    Timestamp,
    date_range,
)
import pandas._testing as tm


def test_applymap(float_frame):
    result = float_frame.applymap(lambda x: x * 2)
    tm.assert_frame_equal(result, float_frame * 2)
    float_frame.applymap(type)

    # GH 465: function returning tuples
    result = float_frame.applymap(lambda x: (x, x))["A"][0]
    assert isinstance(result, tuple)


@pytest.mark.parametrize("val", [1, 1.0])
def test_applymap_float_object_conversion(val):
    # GH 2909: object conversion to float in constructor?
    df = DataFrame(data=[val, "a"])
    result = df.applymap(lambda x: x).dtypes[0]
    assert result == object


@pytest.mark.parametrize("na_action", [None, "ignore"])
def test_applymap_keeps_dtype(na_action):
    # GH52219
    arr = Series(["a", np.nan, "b"])
    sparse_arr = arr.astype(pd.SparseDtype(object))
    df = DataFrame(data={"a": arr, "b": sparse_arr})

    def func(x):
        return str.upper(x) if not pd.isna(x) else x

    result = df.applymap(func, na_action=na_action)

    expected_sparse = pd.array(["A", np.nan, "B"], dtype=pd.SparseDtype(object))
    expected_arr = expected_sparse.astype(object)
    expected = DataFrame({"a": expected_arr, "b": expected_sparse})

    tm.assert_frame_equal(result, expected)

    result_empty = df.iloc[:0, :].applymap(func, na_action=na_action)
    expected_empty = expected.iloc[:0, :]
    tm.assert_frame_equal(result_empty, expected_empty)


def test_applymap_str():
    # GH 2786
    df = DataFrame(np.random.random((3, 4)))
    df2 = df.copy()
    cols = ["a", "a", "a", "a"]
    df.columns = cols

    expected = df2.applymap(str)
    expected.columns = cols
    result = df.applymap(str)
    tm.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "col, val",
    [["datetime", Timestamp("20130101")], ["timedelta", pd.Timedelta("1 min")]],
)
def test_applymap_datetimelike(col, val):
    # datetime/timedelta
    df = DataFrame(np.random.random((3, 4)))
    df[col] = val
    result = df.applymap(str)
    assert result.loc[0, col] == str(df.loc[0, col])


@pytest.mark.parametrize(
    "expected",
    [
        DataFrame(),
        DataFrame(columns=list("ABC")),
        DataFrame(index=list("ABC")),
        DataFrame({"A": [], "B": [], "C": []}),
    ],
)
@pytest.mark.parametrize("func", [round, lambda x: x])
def test_applymap_empty(expected, func):
    # GH 8222
    result = expected.applymap(func)
    tm.assert_frame_equal(result, expected)


def test_applymap_kwargs():
    # GH 40652
    result = DataFrame([[1, 2], [3, 4]]).applymap(lambda x, y: x + y, y=2)
    expected = DataFrame([[3, 4], [5, 6]])
    tm.assert_frame_equal(result, expected)


def test_applymap_na_ignore(float_frame):
    # GH 23803
    strlen_frame = float_frame.applymap(lambda x: len(str(x)))
    float_frame_with_na = float_frame.copy()
    mask = np.random.randint(0, 2, size=float_frame.shape, dtype=bool)
    float_frame_with_na[mask] = pd.NA
    strlen_frame_na_ignore = float_frame_with_na.applymap(
        lambda x: len(str(x)), na_action="ignore"
    )
    strlen_frame_with_na = strlen_frame.copy()
    strlen_frame_with_na[mask] = pd.NA
    tm.assert_frame_equal(strlen_frame_na_ignore, strlen_frame_with_na)


def test_applymap_box_timestamps():
    # GH 2689, GH 2627
    ser = Series(date_range("1/1/2000", periods=10))

    def func(x):
        return (x.hour, x.day, x.month)

    # it works!
    DataFrame(ser).applymap(func)


def test_applymap_box():
    # ufunc will not be boxed. Same test cases as the test_map_box
    df = DataFrame(
        {
            "a": [Timestamp("2011-01-01"), Timestamp("2011-01-02")],
            "b": [
                Timestamp("2011-01-01", tz="US/Eastern"),
                Timestamp("2011-01-02", tz="US/Eastern"),
            ],
            "c": [pd.Timedelta("1 days"), pd.Timedelta("2 days")],
            "d": [
                pd.Period("2011-01-01", freq="M"),
                pd.Period("2011-01-02", freq="M"),
            ],
        }
    )

    result = df.applymap(lambda x: type(x).__name__)
    expected = DataFrame(
        {
            "a": ["Timestamp", "Timestamp"],
            "b": ["Timestamp", "Timestamp"],
            "c": ["Timedelta", "Timedelta"],
            "d": ["Period", "Period"],
        }
    )
    tm.assert_frame_equal(result, expected)


def test_frame_applymap_dont_convert_datetime64():
    from pandas.tseries.offsets import BDay

    df = DataFrame({"x1": [datetime(1996, 1, 1)]})

    df = df.applymap(lambda x: x + BDay())
    df = df.applymap(lambda x: x + BDay())

    result = df.x1.dtype
    assert result == "M8[ns]"


def test_applymap_function_runs_once():
    df = DataFrame({"a": [1, 2, 3]})
    values = []  # Save values function is applied to

    def reducing_function(val):
        values.append(val)

    def non_reducing_function(val):
        values.append(val)
        return val

    for func in [reducing_function, non_reducing_function]:
        del values[:]

        df.applymap(func)
        assert values == df.a.to_list()


def test_applymap_type():
    # GH 46719
    df = DataFrame(
        {"col1": [3, "string", float], "col2": [0.25, datetime(2020, 1, 1), np.nan]},
        index=["a", "b", "c"],
    )

    result = df.applymap(type)
    expected = DataFrame(
        {"col1": [int, str, type], "col2": [float, datetime, float]},
        index=["a", "b", "c"],
    )
    tm.assert_frame_equal(result, expected)


def test_applymap_invalid_na_action(float_frame):
    # GH 23803
    with pytest.raises(ValueError, match="na_action must be .*Got 'abc'"):
        float_frame.applymap(lambda x: len(str(x)), na_action="abc")
