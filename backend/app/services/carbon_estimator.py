DEFAULT_POWER_WATTS = 50.0
DEFAULT_CARBON_INTENSITY = 500.0


def estimate_energy(
    execution_time_ms: float,
    power_watts: float = DEFAULT_POWER_WATTS
):
    """
    Estimate energy consumption in Wh.

    This is a model-based estimate, not direct hardware measurement.
    """

    if execution_time_ms < 0:
        raise ValueError("Execution time cannot be negative.")

    if power_watts <= 0:
        raise ValueError("Power consumption must be positive.")

    energy_wh = (
        execution_time_ms * power_watts
    ) / 3_600_000

    return energy_wh


def estimate_carbon(
    energy_wh: float,
    carbon_intensity: float = DEFAULT_CARBON_INTENSITY
):
    """
    Estimate carbon emissions in grams of CO2 equivalent.
    """

    if energy_wh < 0:
        raise ValueError("Energy cannot be negative.")

    if carbon_intensity < 0:
        raise ValueError("Carbon intensity cannot be negative.")

    energy_kwh = energy_wh / 1000

    carbon_grams = (
        energy_kwh * carbon_intensity
    )

    return carbon_grams


def estimate_environmental_impact(
    execution_time_ms: float,
    power_watts: float = DEFAULT_POWER_WATTS,
    carbon_intensity: float = DEFAULT_CARBON_INTENSITY
):
    energy_wh = estimate_energy(
        execution_time_ms,
        power_watts
    )

    carbon_grams = estimate_carbon(
        energy_wh,
        carbon_intensity
    )

    return {
        "execution_time_ms": execution_time_ms,
        "assumed_power_watts": power_watts,
        "carbon_intensity_g_per_kwh": carbon_intensity,
        "energy_wh": energy_wh,
        "energy_kwh": energy_wh / 1000,
        "carbon_grams_co2e": carbon_grams
    }