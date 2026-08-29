import forecast_evaluation as fe
import forecast_realtime as rt
import news_decomp as nd
import pytest

pytestmark = pytest.mark.contract


def test_authoritative_public_contract_exports_are_available():
    expected_exports = {
        fe: ("ForecastData", "NowcastData", "DensityForecastData"),
        rt: ("ForecastModel", "RealTimeModel"),
        nd: ("NewsData",),
    }

    for module, names in expected_exports.items():
        for name in names:
            exported = getattr(module, name)
            assert isinstance(exported, type)
            assert exported.__name__ == name
