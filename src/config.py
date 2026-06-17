# src/config.py

# Tickers
TICKERS = {
    'Crude_Oil': 'CL=F',
    'Gasoline': 'RB=F',
    'Heating_Oil': 'HO=F',
    'Natural_Gas': 'NG=F',
    'Valero': 'VLO',
    'Phillips66': 'PSX'
}

# Legacy — kept for report_generator.py backward compat
VLO_DEFAULTS = {
    'throughput_bpd': 2_900_000,
    'capture_rate': 0.85,
    'current_ebitda': 14_000_000_000,
    'ev_ebitda_multiple': 6.5,
    'shares_outstanding': 340_000_000
}

# Per-refiner valuation assumptions
REFINER_CONFIGS = {
    'Valero (VLO)': {
        'ticker_col': 'Valero',
        'throughput_bpd': 2_900_000,
        'capture_rate': 0.85,
        'current_ebitda': 14_000_000_000,
        'ev_ebitda_multiple': 6.5,
        'shares_outstanding': 340_000_000,
    },
    'Phillips 66 (PSX)': {
        'ticker_col': 'Phillips66',
        'throughput_bpd': 1_900_000,
        'capture_rate': 0.82,
        'current_ebitda': 5_500_000_000,
        'ev_ebitda_multiple': 7.0,
        'shares_outstanding': 420_000_000,
    },
}

# Crack spread formula definitions
# Ratios: (gasoline_bbls, heating_oil_bbls, crude_bbls)
CRACK_FORMULAS = {
    '3:2:1 (Standard)': {
        'col': 'Crack_Spread',   # pre-computed in pipeline — use directly
        'ratios': (2, 1, 3),
        'label': '3:2:1',
        'description': '2 parts RBOB gasoline + 1 part heating oil from 3 barrels crude. '
                       'Standard US Gulf Coast benchmark formula.',
    },
    '5:3:2 (Heavy Crude)': {
        'col': None,
        'ratios': (3, 2, 5),
        'label': '5:3:2',
        'description': '3 parts RBOB + 2 parts heating oil from 5 barrels crude. '
                       'Used for complex refiners running heavier feedstocks (e.g. cokers).',
    },
    '2:1:1 (Balanced)': {
        'col': None,
        'ratios': (1, 1, 2),
        'label': '2:1:1',
        'description': '1 part RBOB + 1 part heating oil from 2 barrels crude. '
                       'Distillate-balanced; useful when diesel demand dominates.',
    },
}

# OpEx Assumptions
OPEX_DEFAULTS = {
    'nat_gas_intensity': 0.45,  # MMBtu of NatGas per barrel of crude processed
    'fixed_opex': 6.00          # Fixed OpEx (labor, maintenance, catalysts) in $/bbl
}

MARKET_EVENTS = [
    ('2020-03-01', 'COVID Crash'),
    ('2022-02-24', 'Russia-Ukraine War'),
    ('2022-06-01', 'Peak Refining Margins')
]
