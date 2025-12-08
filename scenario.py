import nest_asyncio
nest_asyncio.apply()

import random
from pprint import pprint
import mosaik

STEP = 900  # 15 minuti
END = 3600 * 4  # 4 ore

SIM_CONFIG = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "pv_simulator_kw:PVSimulatorKW"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}

with mosaik.World(SIM_CONFIG) as world:
    # --- Start simulators ---
    weathersim = world.start("Weather", sim_id="Weather", step_size=STEP)
    pvsim = world.start("PV", sim_id="PV", step_size=STEP)
    outputsim = world.start("Output")

    # --- Weather: genera valori casuali tra 0 e 1000 W/m2 ---
    weather = weathersim.Function(function=lambda t: random.uniform(0, 1000))

    # --- Crea PV con limite 6 kW ---
    pvs = [pvsim.PVKW.create(
            1, area=10 +i*0.1, latitude=53.14, efficiency=0.5, el_tilt=32.0, az_tilt=0.0 
        )[0]
        for i in range(2)
    ]

    # --- Connect Weather → PV ---
    for pv in pvs:
        world.connect(weather, pv, ("value", "DNI[W/m2]"))

    # --- Connect PV → OutputSimulator ---
    output = outputsim.Dict()
    for pv in pvs:
        world.connect(pv, output, "P[kW]")

    # --- Run simulation ---
    world.run(until=END)

    # --- Get results from OutputSimulator ---
    result = outputsim.get_dict(output.eid)
    pprint(result)
