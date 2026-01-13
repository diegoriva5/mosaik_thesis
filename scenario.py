import nest_asyncio
nest_asyncio.apply()

import random
from pprint import pprint
import mosaik

STEP = 3600  # 1 ora
END = 3600 * 2  # 24 ore

SIM_CONFIG = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV": {"python": "pv_simulator_kw:PVSimulatorKW"},
    "LoadPred": {"python": "load_profile_simulator:LoadProfileSimulator"},
    "LoadRT": {"python": "load_profile_simulator:LoadProfileSimulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}

# Percorso al CSV dei profili di carico
LOAD_CSV_PATH_PRED = "csv_data/load_istat_social_groups.csv"
LOAD_CSV_PATH_RT = "csv_data/rt_consumes.csv"

with mosaik.World(SIM_CONFIG) as world:
    # --- Start simulators ---
    weathersim = world.start("Weather", sim_id="Weather", step_size=STEP)
    pvsim = world.start("PV", sim_id="PV", step_size=STEP)
    load_pred_sim = world.start("LoadPred", sim_id="LoadPred", csv_path=LOAD_CSV_PATH_PRED, step_size=STEP)
    load_rt_sim = world.start("LoadRT", sim_id="LoadRT", csv_path=LOAD_CSV_PATH_RT, step_size=STEP)
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
    profile_ids = [str(i) for i in range(10)]

    loads_pred = []
    loads_rt = []

    for pid in profile_ids:
        loads_pred.append(
            load_pred_sim.LoadProfile.create(1, profile_id=pid)[0]
        )
        loads_rt.append(
            load_rt_sim.LoadProfile.create(1, profile_id=pid)[0]
        )


    # --- Connect PV + Load -> OutputSimulator ---
    output = outputsim.Dict()
    for pv in pvs:
        world.connect(pv, output, "P[kW]")

    for lp in loads_pred:
        world.connect(lp, output, "P_load[kW]")

    for lr in loads_rt:
        world.connect(lr, output, "P_load[kW]")

    # --- Run simulation ---
    world.run(until=END)

    # --- Get results from OutputSimulator ---
    result = outputsim.get_dict(output.eid)
    pprint(result)
