import nest_asyncio
nest_asyncio.apply()

import random
from pprint import pprint
import mosaik

STEP = 3600  # 1 ora
END = 3600 * 12 # 12 ore

SIM_CONFIG = {
    "Weather": {"python": "mosaik.basic_simulators:InputSimulator"},
    "PV_DA": {"python": "pv_DA_production_simulator:PVDAProductionSimulator"},
    "PV": {"python": "pv_simulator_kw:PVSimulatorKW"},
    "LoadPred": {"python": "load_profile_simulator:LoadProfileSimulator"},
    "LoadRT": {"python": "load_profile_simulator:LoadProfileSimulator"},
    "SmartMeter": {"python": "smart_meter_simulator:SmartMeterSimulator"},
    # "DAMarket": {"python": "DA_market_simulator:DAMarketSimulator"},
    "Output": {"python": "mosaik.basic_simulators:OutputSimulator"},
}

# Percorso al CSV dei profili di carico
LOAD_CSV_PATH_PRED = "csv_data/load_istat_social_groups.csv"
LOAD_CSV_PATH_RT = "csv_data/rt_consumes.csv"
PV_DA_CSV_PATH = "csv_data/pv_DA_production_prediction.csv"

with mosaik.World(SIM_CONFIG) as world:
    # --- Start simulators ---
    weathersim = world.start(
        "Weather", 
        sim_id="Weather", 
        step_size=STEP
    )

    pvsim = world.start(
        "PV", 
        sim_id="PV", 
        step_size=STEP
    )

    pv_da_sim = world.start(
        "PV_DA",
        sim_id="PV_DA",
        csv_path=PV_DA_CSV_PATH,
        step_size=STEP
    )

    load_pred_sim = world.start(
        "LoadPred", 
        sim_id="LoadPred", 
        csv_path=LOAD_CSV_PATH_PRED, 
        step_size=STEP
    )

    load_rt_sim = world.start(
        "LoadRT", 
        sim_id="LoadRT", 
        csv_path=LOAD_CSV_PATH_RT, 
        step_size=STEP
    )

    smart_sim = world.start(
        "SmartMeter",
        sim_id="SmartMeter",
        step_size=STEP
    )
    
    """ da_market = world.start(
        "DAMarket",
        sim_id="DAMarket",
        step_size=STEP
    ) """
    
    outputsim = world.start("Output")

    # --- Weather: genera valori casuali tra 0 e 1000 W/m2 ---
    weather = weathersim.Function(function=lambda t: random.uniform(0, 1000))

    profile_ids = [str(i) for i in range(10)]   # Ho 10 profili di carico e faccio dipendere
                                                # la produzione PV (cambia l'area) dallo 
                                                # stesso ID

    # --- Crea PV con limite 6 kW ---
    pvs = [pvsim.HomePV.create(
            1, 
            profile_id=pid,
            area=10 +float(pid)*0.1,    # Cast a float per calcolo dell'area
            latitude=53.14, 
            efficiency=0.5, 
            el_tilt=32.0, 
            az_tilt=0.0 
        )[0]
        for pid in profile_ids
    ]

    # --- Connect Weather → PV ---
    for pv in pvs:
        world.connect(weather, pv, ("value", "DNI[W/m2]"))

    # -----------------------------
    # PV Day-Ahead production profiles
    # -----------------------------
    pv_da_profiles = []

    for pid in profile_ids:
        pv_da_profiles.append(
            pv_da_sim.PV_DA_Production.create(
                1,
                profile_id=pid
            )[0]
        )

    # -----------------------------
    # Load profiles creation
    # -----------------------------
    # CSV contiene colonne '0' a '9' (da usare come profile_id)

    loads_pred = []
    loads_rt = []

    for pid in profile_ids:
        loads_pred.append(
            load_pred_sim.LoadProfile.create(1, profile_id=pid)[0]
        )
        loads_rt.append(
            load_rt_sim.LoadProfile.create(1, profile_id=pid)[0]
        )

    # -------------------------
    # Smart Meters creation
    # -------------------------
    smart_meters = []

    for pid in profile_ids:
        sm = smart_sim.SmartMeter.create(
            1,
            profile_id=pid
        )[0]
        smart_meters.append(sm)
    # -------------------------
    # DA Market creation
    # -------------------------
    """ market = da_market.DAMarket.create(1)[0] """

    # -------------------------------------------------
    # CONNECTIONS
    # -------------------------------------------------
    for pv, pv_da, lp, lr, sm in zip(pvs, pv_da_profiles, loads_pred, loads_rt, smart_meters):
        # PV → SmartMeter
        world.connect(pv, sm, ("P[kW]", "P_PV_RT_Production[kW]"))

        # PV DA → SmartMeter
        world.connect(pv_da, sm, ("PV_DA_Prod_Prediction[kW]+24h", "PV_DA_Prod_Prediction[kW]+24h"))

        # LoadPred → SmartMeter (Day-Ahead)
        world.connect(lp, sm, ("P_load_DA+24h[kW]", "P_load_DA_Prevision[kW]+24h"))

        # LoadRT → SmartMeter (Real-Time)
        world.connect(lr, sm, ("P_load_DA+24h[kW]", "P_load_RT[kW]"))

    # --- Connect PV + Load -> OutputSimulator ---
    output = outputsim.Dict()
    for sm in smart_meters:
        world.connect(
            sm,
            output,
            "PV_DA_Prod_Prediction[kW]+24h",
            # "P_PV_RT_Production[kW]",
            "P_load_DA_Prevision[kW]+24h",
            # "P_load_RT[kW]",

            # "P_DA_committed[kW]",
            # "P_RT_committed[kW]",

            # "P_net_DA[kW]",
            # "P_net_phys_RT[kW]",
            # "P_net_RT[kW]",
        )
    
    # --- Run simulation ---
    world.run(until=END)

    # --- Get results from OutputSimulator ---
    result = outputsim.get_dict(output.eid)
    pprint(result)
