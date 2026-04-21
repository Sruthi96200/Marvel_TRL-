# config/subsystems.py
# MARVEL microreactor subsystem definitions with targeted search terms

MARVEL_SUBSYSTEMS = {
    "heat_transport": {
        "name": "Heat Transport System (Heat Pipes)",
        "description": "Passive heat pipe system using sodium or NaK for heat removal from reactor core",
        "osti_queries": [
            "MARVEL microreactor heat pipe",
            "heat pipe nuclear microreactor sodium",
            "microreactor heat pipe TRL readiness",
            "INL heat pipe reactor thermal transport",
            "heat pipe wick nuclear passive cooling"
        ],
        "arxiv_queries": [
            "heat pipe nuclear microreactor MARVEL",
            "sodium heat pipe reactor thermal",
            "passive heat removal microreactor heat pipe"
        ],
        "relevance_keywords": [
            "heat pipe", "heat transport", "thermal transport", "passive cooling",
            "sodium", "NaK", "wick", "microreactor", "MARVEL", "INL",
            "evaporator", "condenser", "vapor core", "heat pipe failure"
        ]
    },
    "reactor_core": {
        "name": "Reactor Core and Fuel System",
        "description": "SNAP-10A heritage fuel, yttrium hydride moderator, uranium fuel elements",
        "osti_queries": [
            "MARVEL reactor core fuel yttrium hydride",
            "microreactor uranium fuel SNAP heritage",
            "yttrium hydride moderator nuclear reactor",
            "MARVEL neutronics fuel assembly INL",
            "microreactor fuel element qualification"
        ],
        "arxiv_queries": [
            "yttrium hydride moderator nuclear microreactor",
            "SNAP reactor fuel nuclear microreactor",
            "uranium fuel microreactor neutronics"
        ],
        "relevance_keywords": [
            "yttrium hydride", "YH", "fuel element", "SNAP", "reactor core",
            "moderator", "neutronics", "uranium", "enriched", "MARVEL",
            "fuel qualification", "burnup", "fission"
        ]
    },
    "power_conversion": {
        "name": "Power Conversion System (Stirling Engines)",
        "description": "Stirling engine power conversion converting reactor heat to electricity",
        "osti_queries": [
            "Stirling engine nuclear microreactor power conversion",
            "MARVEL Stirling engine electricity generation",
            "free piston Stirling nuclear power",
            "microreactor power conversion TRL",
            "Stirling convertor space nuclear power"
        ],
        "arxiv_queries": [
            "Stirling engine nuclear reactor power conversion",
            "free piston Stirling microreactor",
            "nuclear Stirling engine efficiency"
        ],
        "relevance_keywords": [
            "Stirling", "power conversion", "free piston", "electricity generation",
            "kWe", "kilowatt electric", "MARVEL", "thermal to electric",
            "convertor", "heat engine", "power cycle"
        ]
    },
    "control_systems": {
        "name": "Control and Instrumentation Systems",
        "description": "Autonomous reactor control, instrumentation, digital I&C, remote monitoring",
        "osti_queries": [
            "MARVEL microreactor autonomous control system",
            "nuclear microreactor digital instrumentation control",
            "autonomous reactor control INL microreactor",
            "microreactor remote monitoring I&C",
            "nuclear digital control system TRL readiness"
        ],
        "arxiv_queries": [
            "autonomous nuclear reactor control system",
            "microreactor instrumentation digital control",
            "nuclear I&C machine learning autonomous"
        ],
        "relevance_keywords": [
            "autonomous", "control rod", "instrumentation", "I&C", "digital control",
            "remote monitoring", "MARVEL", "microreactor", "reactor control",
            "safety system", "SCRAM", "reactivity control"
        ]
    },
    "safety_systems": {
        "name": "Safety and Shutdown Systems",
        "description": "Passive safety, decay heat removal, shutdown mechanisms",
        "osti_queries": [
            "microreactor passive safety shutdown system",
            "MARVEL reactor safety decay heat removal",
            "nuclear microreactor inherent safety passive",
            "microreactor shutdown mechanism safety case",
            "heat pipe reactor passive safety NRC"
        ],
        "arxiv_queries": [
            "passive safety microreactor shutdown",
            "nuclear microreactor decay heat passive removal",
            "inherent safety heat pipe reactor"
        ],
        "relevance_keywords": [
            "passive safety", "decay heat", "shutdown", "inherent safety",
            "SCRAM", "safety case", "NRC", "licensing", "MARVEL",
            "microreactor safety", "fail-safe", "negative feedback"
        ]
    },
    "grid_integration": {
        "name": "Grid Integration and Load Coupling",
        "description": "Connecting microreactor to load (data center, microgrid), power management",
        "osti_queries": [
            "nuclear microreactor grid integration data center",
            "MARVEL reactor load following power grid",
            "microreactor microgrid coupling nuclear",
            "nuclear data center power supply ASU MARVEL",
            "small reactor load coupling electricity grid"
        ],
        "arxiv_queries": [
            "nuclear microreactor grid integration load",
            "microreactor data center power coupling",
            "small nuclear reactor microgrid"
        ],
        "relevance_keywords": [
            "grid integration", "load following", "microgrid", "data center",
            "power management", "MARVEL", "ASU", "load coupling",
            "electricity supply", "nuclear data center", "grid stability"
        ]
    }
}