import nest_asyncio
nest_asyncio.apply()

import random
import mosaik

SIM_CONFIG = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "pv_simulator_kw:PVSimulatorKW"},
}

STEP = 900       # 15 minuti
END = 3600 * 4   # 4 ore di simulazione

with mosaik.World(SIM_CONFIG) as world:
    # --- Avvio simulatori ---
    weathersim = world.start("Weather", sim_id="Weather", step_size=STEP)
    pvsim = world.start("PV", sim_id="PV", step_size=STEP, start_date="2023-06-01 12:00:00")

    # --- Funzione Weather ---
    weather = weathersim.Function(function=lambda t: random.uniform(0, 1000))  # W/m2

    # --- Creazione PV ---
    pvs = pvsim.PVKW.create(
        5,  # numero di pannelli PV
        area=10,
        efficiency=0.18,
        latitude=45.0,
        el_tilt=30.0,
        az_tilt=0.0
    )

    # --- Collegamento Weather → PVKW ---
    for pv_entity in pvs:
        world.connect(weather, pv_entity, ('value', 'DNI[W/m2]'))

    # --- Avvio simulazione ---
    world.run(until=END)
