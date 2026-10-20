"""V87 frozen metadata draw, committed BEFORE opening any novel body.

The metadata-only Railway receipt on deployment
d2f134a7-d7bd-44e0-963a-b7550e0c7ca1 established this plan.
Any changed inventory/candidate ordering => fail closed; no reselection.
"""
PLAN_SHA256="ddb50ed6b88681c23d214073d45ba4edba151bf0de1e0bfed5153efeeb3e1f6c"
CATALOG_SHA256="c1fdf9ac6e089ce2fffd78d4caf7cea2a186ef48016a9e076371baa1f4bc4e04"
SEED_SHA256="cb36891f420b045d6816f05f4bfe6de01779c0d05b9f3e7eee4dd1c3ba61dfe3"
FROZEN_DRAWS=(
    ("历史",(
        "3f97f5e4748a3782a1c3d21119d9c193798de895b6db9969fede325de4de916f",
        "7ade357517465167c6ea48fbaec2815f01c7e181603c3189157e9fb3adc6bbde",
        "ee1a6a22a548a76b27e5ff8d15472f6aeecbd9e8b7e60416f0faa8f85c4b2aa9",
        "7e12b27ddad2fc8177cbb846aedff7fa8949fcd40aec80c948ceab78dd5d0485",
    )),
    ("科幻",(
        "adf902299d736482069001d109c15f087513cef78258f62529b2e0b5e15c30e6",
        "bf474a0bc98f78f3787393a5ef74f5771447962b13c20f042d32a53a0bb17380",
        "56a390fece5a4eb015cc67e6dd51f3e87814c1c2d8842c7a770d371056f49d7a",
    )),
)
EXCLUDE_ALREADY_USED_SOURCE_SHA256=(
    "0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd",
    "e3fb51aa6d9ed50f79c7c9d60361a366c4a168b8593d1cdaaec65784e46f8cd8",
)
