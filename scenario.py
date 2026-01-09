import nest_asyncio
nest_asyncio.apply()

import random
from pprint import pprint
import mosaik

STEP = 3600  # 1 ora
END = 3600 * 24  # 24 ore

SIM_CONFIG = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "pv_simulator_kw:PVSimulatorKW"},
    "Load": {"python": "load_profile_simulator:LoadProfileSimulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}

# Percorso al CSV dei profili di carico
LOAD_CSV_PATH = "load_istat_social_groups.csv"

with mosaik.World(SIM_CONFIG) as world:
    # --- Start simulators ---
    weathersim = world.start("Weather", sim_id="Weather", step_size=STEP)
    pvsim = world.start("PV", sim_id="PV", step_size=STEP)
    loadsim = world.start("Load", sim_id="Load", csv_path=LOAD_CSV_PATH, step_size=STEP)
    outputsim = world.start("Output")

    # --- Weather: genera valori casuali tra 0 e 1000 W/m2 ---
    weather = weathersim.Function(function=lambda t: random.uniform(0, 1000))

    # --- Crea PV con limite 6 kW ---
    pvs = [pvsim.PVKW.create(
            1, area=10 +i*0.1, latitude=53.14, efficiency=0.5, el_tilt=32.0, az_tilt=0.0 
        )[0]
        for i in range(10)
    ]

    # --- Connect Weather → PV ---
    for pv in pvs:
        world.connect(weather, pv, ("value", "DNI[W/m2]"))

    # -----------------------------
    # Load profiles creation
    # -----------------------------
    # CSV contiene colonne '0' a '9' (da usare come profile_id)
    loads = []
    for profile_id in [str(i) for i in range(10)]:
        loads += loadsim.LoadProfile.create(1, profile_id=profile_id)


    # --- Connect PV + Load -> OutputSimulator ---
    output = outputsim.Dict()
    for pv in pvs:
        world.connect(pv, output, "P[kW]")
    for load in loads:
        world.connect(load, output, "P_load[kW]")

    # --- Run simulation ---
    world.run(until=END)

    # --- Get results from OutputSimulator ---
    result = outputsim.get_dict(output.eid)
    pprint(result)
