rules:
  - id: CSN730802_8_15_4_A
    title: Střešní plášť jako požárně otevřená plocha
    type: default_rule
    condition: "Pokud není splněna některá výjimka podle 8.15.4 b)"
    result:
      roof_is_fire_open: true
      pv_default_kg_m2: 30
      include_roof_openings: true
    source:
      standard: "ČSN 73 0802"
      article: "8.15.4 a)"

  - id: CSN730802_8_15_4_B1
    title: Střešní plášť není požárně otevřenou plochou – I. a II. SPB
    type: exception_rule
    required_inputs:
      - pv_kg_m2
      - fire_safety_level
      - roof_requirement_status
    condition:
      all:
        - "pv_kg_m2 <= 50"
        - "fire_safety_level in ['I', 'II']"
        - "roof_requirement_status in ['splňuje 8.15.1 a)', 'požadavky 8.15.1 c) jsou nulové']"
    result:
      roof_is_fire_open: false
      distance_required: false
    source:
      standard: "ČSN 73 0802"
      article: "8.15.4 b) 1)"

  - id: CSN730802_8_15_4_B2
    title: Střešní plášť Broof(t3) nad požárním stropem
    type: exception_rule
    required_inputs:
      - roof_classification
      - roof_structure_above_fire_ceiling
      - fire_resistance_required
    condition:
      all:
        - "roof_classification == 'Broof(t3)'"
        - "roof_structure_above_fire_ceiling == true"
        - "fire_resistance_required == false"
    result:
      roof_is_fire_open: false
      distance_required: false
    source:
      standard: "ČSN 73 0802"
      article: "8.15.4 b) 2)"

  - id: CSN730802_8_15_4_B4
    title: Střešní plášť bez požadované požární odolnosti při c <= 0,4
    type: exception_rule
    required_inputs:
      - fire_resistance_required
      - fire_resistance_met
      - coefficient_c
    condition:
      all:
        - "fire_resistance_required == true"
        - "fire_resistance_met == false"
        - "coefficient_c <= 0.4"
    result:
      roof_is_fire_open: false
      distance_required: false
    source:
      standard: "ČSN 73 0802"
      article: "8.15.4 b) 4)"

  - id: CSN730802_8_15_5_A
    title: Určení výšky požárně otevřené plochy střechy hu
    type: calculation_rule
    required_inputs:
      - roof_slope_deg
      - roof_lowest_level_m
      - roof_ridge_level_m
    logic:
      - "Pokud roof_slope_deg < 15, použij hu = 2 m."
      - "Jinak hu = vzdálenost mezi nejnižší úrovní střešního pláště a hřebenem střechy."
    source:
      standard: "ČSN 73 0802"
      article: "8.15.5 a)"

  - id: CSN730802_10_4_4_A
    title: Hustota tepelného toku u zcela požárně otevřených ploch obvodových stěn
    type: calculation_rule
    required_inputs:
      - pv_kg_m2
      - structural_system_type
    logic:
      - "U zcela požárně otevřených ploch je hustota určena výpočtovým požárním zatížením."
      - "U smíšeného konstrukčního systému se pv zvýší o 5 kg/m2."
      - "U hořlavého systému c1 se pv zvýší o 10 kg/m2."
      - "U hořlavého systému c2 se pv zvýší o 15 kg/m2."
    source:
      standard: "ČSN 73 0802"
      article: "10.4.4 a)"

  - id: CSN730802_10_4_4_B
    title: Hustota tepelného toku u částečně požárně otevřených ploch
    type: fixed_value_rule
    result:
      heat_flux_kw_m2: 60
      equivalent_pv_kg_m2: 15
    source:
      standard: "ČSN 73 0802"
      article: "10.4.4 b)"

  - id: CSN730802_10_4_4_C
    title: Hustota tepelného toku u požárně otevřených ploch střešních plášťů
    type: fixed_value_rule
    result:
      heat_flux_kw_m2: 87
      equivalent_pv_kg_m2: 30
    source:
      standard: "ČSN 73 0802"
      article: "10.4.4 c)"

  - id: CSN730802_10_4_6
    title: Zvětšení odstupové vzdálenosti při nebezpečí padání hořících částí
    type: comparison_rule
    required_inputs:
      - base_distance_m
      - fall_height_m
      - falling_burning_parts_risk
    condition: "falling_burning_parts_risk == true"
    calculation:
      falling_distance_m: "0.36 * fall_height_m"
      final_distance_m: "max(base_distance_m, falling_distance_m)"
    source:
      standard: "ČSN 73 0802"
      article: "10.4.6"

  - id: CSN730802_10_4_7
    title: Kdy se neprovádí porovnání podle 10.4.6
    type: exception_rule
    conditions_any:
      - "Obvodové a střešní pláště jsou DP1."
      - "Obvodové a střešní pláště jsou DP2 a je prokázáno, že padající části nemohou šířit požár."
      - "Jde o odstupové vzdálenosti mezi požárními úseky téhož objektu."
    result:
      falling_parts_assessment_required: false
    source:
      standard: "ČSN 73 0802"
      article: "10.4.7"

  - id: CSN730802_10_4_8_1
    title: Samostatné posuzování jednotlivých požárně otevřených ploch
    type: decision_rule
    required_inputs:
      - p0_percent
      - openings_edge_distance_m
      - distance_opening_1_m
      - distance_opening_2_m
    condition:
      all:
        - "p0_percent < 40"
        - "openings_edge_distance_m > 0.6 * (distance_opening_1_m + distance_opening_2_m)"
    result:
      individual_opening_distances_can_be_used: true
    source:
      standard: "ČSN 73 0802"
      article: "10.4.8.1"

  - id: CSN730810_3_1_3
    title: Vnější zateplení v požárně nebezpečném prostoru jiného objektu
    type: material_requirement
    condition: "Zateplení se nachází v požárně nebezpečném prostoru jiného objektu."
    result:
      required_reaction_to_fire_class: ["A1", "A2"]
    source:
      standard: "ČSN 73 0810"
      article: "3.1.3"