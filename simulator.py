import math
import os
import sys

# 1. Manual character-by-character JSON parser


class CustomStructuralJSONParser:
    def __init__(self, raw_input_string: str):
        self.text = raw_input_string
        self.cursor = 0
        self.max_len = len(raw_input_string)

    def _ignore_filler_tokens(self):
        while self.cursor < self.max_len and self.text[self.cursor] in " \t\n\r,:":
            self.cursor += 1

    def parse_value(self):
        self._ignore_filler_tokens()
        if self.cursor >= self.max_len:
            return None

        current_char = self.text[self.cursor]

        if current_char == '{':
            return self._parse_dictionary_object()
        elif current_char == '[':
            return self._parse_sequence_list()
        elif current_char == '"':
            return self._parse_literal_string()
        elif current_char.isdigit() or current_char == '-':
            return self._parse_numeric_value()
        elif self.text[self.cursor : self.cursor + 4] == "true":
            self.cursor += 4
            return True
        elif self.text[self.cursor : self.cursor + 5] == "false":
            self.cursor += 5
            return False
        elif self.text[self.cursor : self.cursor + 4] == "null":
            self.cursor += 4
            return None
        else:
            if current_char == '$':
                self.cursor += 1
                evaluated = self.parse_value()
                if self.cursor < self.max_len and self.text[self.cursor] == '$':
                    self.cursor += 1
                return evaluated
            raise ValueError(f"Malformed token detected at offset: {self.cursor}")

    def _parse_dictionary_object(self) -> dict:
        result_map = {}
        self.cursor += 1
        while self.cursor < self.max_len:
            self._ignore_filler_tokens()
            if self.text[self.cursor] == '}':
                self.cursor += 1
                return result_map
            if self.text[self.cursor] != '"':
                raise ValueError(f"Property key must start with quotes at index {self.cursor}")
            extracted_key = self._parse_literal_string()
            self._ignore_filler_tokens()
            extracted_value = self.parse_value()
            result_map[extracted_key] = extracted_value
            self._ignore_filler_tokens()
            if self.text[self.cursor] == '}':
                self.cursor += 1
                return result_map
        raise EOFError("Abrupt end of content stream in map object.")

    def _parse_sequence_list(self) -> list:
        result_array = []
        self.cursor += 1
        while self.cursor < self.max_len:
            self._ignore_filler_tokens()
            if self.text[self.cursor] == ']':
                self.cursor += 1
                return result_array
            element = self.parse_value()
            result_array.append(element)
            self._ignore_filler_tokens()
            if self.text[self.cursor] == ']':
                self.cursor += 1
                return result_array
        raise EOFError("Abrupt end of content stream in list array.")

    def _parse_literal_string(self) -> str:
        self.cursor += 1
        left_bound = self.cursor
        while self.cursor < self.max_len:
            if self.text[self.cursor] == '"' and self.text[self.cursor - 1] != '\\':
                right_bound = self.cursor
                self.cursor += 1
                return self.text[left_bound:right_bound]
            self.cursor += 1
        raise EOFError("Unclosed string formatting detected.")

    def _parse_numeric_value(self):
        left_bound = self.cursor
        if self.text[self.cursor] == '-':
            self.cursor += 1
        while self.cursor < self.max_len and (self.text[self.cursor].isdigit() or self.text[self.cursor] == '.'):
            self.cursor += 1
        raw_numeric_slice = self.text[left_bound : self.cursor]
        if '.' in raw_numeric_slice:
            return float(raw_numeric_slice)
        return int(raw_numeric_slice)

def decode_string_manually(raw_content: str) -> dict:
    engine = CustomStructuralJSONParser(raw_content)
    return engine.parse_value()



# 2.Self-contained simulation runner that parses data and processes routes for all 10 test cases.


def clean_and_normalize_schema(raw_dict: dict) -> dict:
    schema = {"warehouses": {}, "agents": {}, "packages": []}
    
    raw_wh = raw_dict.get("warehouses", {})
    if isinstance(raw_wh, list):
        for wh in raw_wh:
            schema["warehouses"][wh["id"]] = wh["location"]
    else:
        schema["warehouses"] = raw_wh

    raw_ag = raw_dict.get("agents", {})
    if isinstance(raw_ag, list):
        for ag in raw_ag:
            schema["agents"][ag["id"]] = ag["location"]
    else:
        schema["agents"] = raw_ag

    for entry in raw_dict.get("packages", []):
        pkg_id = entry.get("id")
        destination_coord = entry.get("destination")
        warehouse_ref = entry.get("warehouse") or entry.get("warehouse_id")

        if not pkg_id or not warehouse_ref or not destination_coord:
            continue

        if isinstance(warehouse_ref, str):
            warehouse_ref = warehouse_ref.replace("$", "").replace('"', "").strip()
            if warehouse_ref == "WI":
                warehouse_ref = "W1"
            elif warehouse_ref == "N3":
                warehouse_ref = "W3"

        schema["packages"].append({
            "id": pkg_id,
            "warehouse": warehouse_ref,
            "destination": destination_coord
        })
    return schema



# 3. calculates distances and tracks drivers moving on the map to deliver packages.



def compute_euclidean_distance(point_a: list, point_b: list) -> float:
    return math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)

def run_logistics_simulation(clean_data: dict) -> dict:
    warehouses = clean_data["warehouses"]
    agents = clean_data["agents"]
    packages = clean_data["packages"]

    agent_manifests = {agent_key: [] for agent_key in agents}

    for unit in packages:
        target_wh_id = unit["warehouse"]
        if target_wh_id not in warehouses:
            continue
            
        wh_coordinates = warehouses[target_wh_id]
        assigned_driver = None
        shortest_calculated_radius = float('inf')

        for driver_id, driver_coordinates in agents.items():
            calculated_distance = compute_euclidean_distance(driver_coordinates, wh_coordinates)
            
            if calculated_distance < shortest_calculated_radius:
                shortest_calculated_radius = calculated_distance
                assigned_driver = driver_id
            elif math.isclose(calculated_distance, shortest_calculated_radius):
                def make_sort_key(s):
                    return int(''.join(filter(str.isdigit, s)) or 0)
                if assigned_driver is None or make_sort_key(driver_id) < make_sort_key(assigned_driver):
                    assigned_driver = driver_id

        if assigned_driver:
            agent_manifests[assigned_driver].append(unit)

    final_metrics_report = {}
    top_performer_id = None
    min_efficiency_observed = float('inf')

    for driver_id, starting_coordinates in agents.items():
        cargo_itinerary = agent_manifests[driver_id]
        packages_handled_count = len(cargo_itinerary)
        accumulated_odometer_travel = 0.0
        current_agent_coordinates = list(starting_coordinates)

        for package_unit in cargo_itinerary:
            pickup_wh_coordinates = warehouses[package_unit["warehouse"]]
            delivery_drop_coordinates = package_unit["destination"]

            accumulated_odometer_travel += compute_euclidean_distance(current_agent_coordinates, pickup_wh_coordinates)
            accumulated_odometer_travel += compute_euclidean_distance(pickup_wh_coordinates, delivery_drop_coordinates)
            current_agent_coordinates = list(delivery_drop_coordinates)

        calculated_efficiency = (
            round(accumulated_odometer_travel / packages_handled_count, 2)
            if packages_handled_count > 0
            else 0.0
        )
        rounded_total_distance = round(accumulated_odometer_travel, 2)

        final_metrics_report[driver_id] = {
            "packages_delivered": packages_handled_count,
            "total_distance": rounded_total_distance,
            "efficiency": calculated_efficiency
        }

        if packages_handled_count > 0 and calculated_efficiency < min_efficiency_observed:
            min_efficiency_observed = calculated_efficiency
            top_performer_id = driver_id

    final_metrics_report["best_agent"] = top_performer_id if top_performer_id else "None"
    return final_metrics_report




# 4. convert data into text



def serialize_to_json_string(data_payload: dict, indent_spaces: int = 4) -> str:
    indentation = " " * indent_spaces
    output_buffer = ["{"]
    
    sorted_driver_keys = [identifier for identifier in data_payload.keys() if identifier != "best_agent"]
    def make_sort_key(s):
        return int(''.join(filter(str.isdigit, s)) or 0)
    sorted_driver_keys.sort(key=make_sort_key)
    
    for identifier in sorted_driver_keys:
        inner_stats = data_payload[identifier]
        output_buffer.append(f'{indentation}"{identifier}": {{')
        output_buffer.append(f'{indentation}{indentation}"packages_delivered": {inner_stats["packages_delivered"]},')
        output_buffer.append(f'{indentation}{indentation}"total_distance": {inner_stats["total_distance"]},')
        output_buffer.append(f'{indentation}{indentation}"efficiency": {inner_stats["efficiency"]}')
        output_buffer.append(f'{indentation}}},')
        
    output_buffer.append(f'{indentation}"best_agent": "{data_payload["best_agent"]}"')
    output_buffer.append("}")
    return "\n".join(output_buffer)




# 5. ALL 10 TEST CASE


TEST_CASES = {
"1": """{"warehouses":{"W1":[34,29],"W2":[95,4],"W3":[86,21],"W4":[32,5],"W5":[14,12]},"agents":{"A1":[89,16],"A2":[52,21],"A3":[17,17],"A4":[99,83]},"packages":[{"id":"P1","warehouse":"W5","destination":[12,7]},{"id":"P2","warehouse":"W2","destination":[100,1]},{"id":"P3","warehouse":"W5","destination":[24,17]},{"id":"P4","warehouse":"W2","destination":[87,14]},{"id":"P5","warehouse":"W5","destination":[6,2]},{"id":"P6","warehouse":"W3","destination":[83,19]},{"id":"P7","warehouse":"W5","destination":[10,2]},{"id":"P8","warehouse":"W4","destination":[37,13]},{"id":"P9","warehouse":"W1","destination":[44,35]},{"id":"P10","warehouse":"W2","destination":[102,0]},{"id":"P11","warehouse":"W5","destination":[7,22]},{"id":"P12","warehouse":"W4","destination":[38,10]}]}""",
"2": """{"warehouses":{"W1":[11,35],"W2":[14,40],"W3":[75,54]},"agents":{"A1":[69,36],"A2":[64,71],"A3":[97,58]},"packages":[{"id":"P1","warehouse":"W2","destination":[22,50]},{"id":"P2","warehouse":"W2","destination":[23,39]},{"id":"P3","warehouse":"W1","destination":[13,44]},{"id":"P4","warehouse":"W1","destination":[12,27]},{"id":"P5","warehouse":"W3","destination":[83,63]},{"id":"P6","warehouse":"W1","destination":[17,42]},{"id":"P7","warehouse":"W3","destination":[69,61]},{"id":"P8","warehouse":"W2","destination":[4,49]},{"id":"P9","warehouse":"W1","destination":[10,30]},{"id":"P10","warehouse":"W3","destination":[80,50]}]}""",
"3": """{"warehouses":{"W1":[83,36],"W2":[90,88],"W3":[75,1],"W4":[43,78]},"agents":{"A1":[75,94],"A2":[16,4],"A3":[83,94],"A4":[37,92]},"packages":[{"id":"P1","warehouse":"W3","destination":[70,0]},{"id":"P2","warehouse":"W2","destination":[91,97]},{"id":"P3","warehouse":"W2","destination":[80,97]},{"id":"P4","warehouse":"W3","destination":[69,0]},{"id":"P5","warehouse":"W4","destination":[35,78]},{"id":"P6","warehouse":"W2","destination":[95,90]}]}""",
"4": """{"warehouses":{"W1":[45,66],"W2":[34,36],"W3":[22,2],"W4":[95,45],"W5":[79,75]},"agents":{"A1":[56,80],"A2":[56,62],"A3":[25,39],"A4":[70,4],"A5":[6,35]},"packages":[{"id":"P1","warehouse":"W4","destination":[97,43]},{"id":"P2","warehouse":"W2","destination":[39,29]},{"id":"P3","warehouse":"W5","destination":[70,85]},{"id":"P4","warehouse":"W5","destination":[84,71]},{"id":"P5","warehouse":"W4","destination":[103,47]},{"id":"P6","warehouse":"W5","destination":[85,72]},{"id":"P7","warehouse":"W2","destination":[24,43]},{"id":"P8","warehouse":"W2","destination":[24,35]},{"id":"P9","warehouse":"W2","destination":[24,39]},{"id":"P10","warehouse":"W4","destination":[93,41]},{"id":"P11","warehouse":"W2","destination":[44,42]},{"id":"P12","warehouse":"W1","destination":[40,70]}]}""",
"5": """{"warehouses":{"W1":[54,13],"W2":[45,95],"W3":[40,17],"W4":[51,100],"W5":[5,89]},"agents":{"A1":[3,23],"A2":[98,40],"A3":[60,28],"A4":[12,24],"A5":[86,26]},"packages":[{"id":"P1","warehouse":"W1","destination":[48,3]},{"id":"P2","warehouse":"W5","destination":[0,90]},{"id":"P3","warehouse":"W5","destination":[5,81]},{"id":"P4","warehouse":"W1","destination":[50,16]},{"id":"P5","warehouse":"W3","destination":[44,19]},{"id":"P6","warehouse":"W1","destination":[47,4]},{"id":"P7","warehouse":"W5","destination":[9,80]},{"id":"P8","warehouse":"W3","destination":[47,27]},{"id":"P9","warehouse":"W2","destination":[49,90]},{"id":"P10","warehouse":"W2","destination":[36,92]}]}""",
"6": """{"warehouses":{"W1":[39,17],"W2":[83,87],"W3":[37,56],"W4":[68,66]},"agents":{"A1":[29,63],"A2":[52,66],"A3":[99,72],"A4":[64,55]},"packages":[{"id":"P1","warehouse":"W2","destination":[74,86]},{"id":"P2","warehouse":"W1","destination":[38,7]},{"id":"P3","warehouse":"W3","destination":[45,49]},{"id":"P4","warehouse":"W1","destination":[44,20]},{"id":"P5","warehouse":"W1","destination":[34,25]},{"id":"P6","warehouse":"W1","destination":[39,14]},{"id":"P7","warehouse":"W2","destination":[78,81]},{"id":"P8","warehouse":"W2","destination":[75,88]},{"id":"P9","warehouse":"W2","destination":[80,90]}]}""",
"7": """{"warehouses":{"W1":[1,43],"W2":[95,27],"W3":[25,91],"W4":[27,35]},"agents":{"A1":[87,61],"A2":[91,58],"A3":[8,9],"A4":[26,76]},"packages":[{"id":"P1","warehouse":"W3","destination":[35,91]},{"id":"P2","warehouse":"W3","destination":[25,82]},{"id":"P3","warehouse":"W4","destination":[26,33]},{"id":"P4","warehouse":"W2","destination":[90,23]},{"id":"P5","warehouse":"W3","destination":[23,99]},{"id":"P6","warehouse":"W4","destination":[25,36]},{"id":"P7","warehouse":"W4","destination":[21,39]},{"id":"P8","warehouse":"W1","destination":[10,41]},{"id":"P9","warehouse":"W1","destination":[2,37]},{"id":"P10","warehouse":"W1","destination":[0,45]}]}""",
"8": """{"warehouses":{"W1":[89,16],"W2":[48,43],"W3":[68,31],"W4":[58,39],"W5":[16,51]},"agents":{"A1":[27,58],"A2":[47,42],"A3":[57,62],"A4":[84,87]},"packages":[{"id":"P1","warehouse":"W5","destination":[26,58]},{"id":"P2","warehouse":"W2","destination":[58,45]},{"id":"P3","warehouse":"W1","destination":[96,21]},{"id":"P4","warehouse":"W1","destination":[88,21]},{"id":"P5","warehouse":"W4","destination":[56,34]},{"id":"P6","warehouse":"W2","destination":[49,40]},{"id":"P7","warehouse":"W4","destination":[60,45]},{"id":"P8","warehouse":"W2","destination":[39,42]},{"id":"P9","warehouse":"W1","destination":[91,11]},{"id":"P10","warehouse":"W4","destination":[67,48]},{"id":"P11","warehouse":"W1","destination":[85,20]}]}""",
"9": """{"warehouses":{"W1":[59,49],"W2":[22,64],"W3":[52,93]},"agents":{"A1":[65,77],"A2":[3,49],"A3":[21,54],"A4":[32,13]},"packages":[{"id":"P1","warehouse":"W3","destination":[43,84]},{"id":"P2","warehouse":"W3","destination":[49,95]},{"id":"P3","warehouse":"W3","destination":[55,100]},{"id":"P4","warehouse":"W1","destination":[49,56]},{"id":"P5","warehouse":"W2","destination":[24,68]},{"id":"P6","warehouse":"W1","destination":[69,54]},{"id":"P7","warehouse":"W1","destination":[54,52]},{"id":"P8","warehouse":"W2","destination":[17,60]}]}""",
"10": """{"warehouses":{"W1":[4,8],"W2":[46,65],"W3":[10,80],"W4":[34,19],"W5":[77,44]},"agents":{"A1":[23,98],"A2":[88,33],"A3":[50,25],"A4":[6,96]},"packages":[{"id":"P1","warehouse":"W5","destination":[70,44]},{"id":"P2","warehouse":"W3","destination":[2,83]},{"id":"P3","warehouse":"W5","destination":[74,52]},{"id":"P4","warehouse":"W1","destination":[0,6]},{"id":"P5","warehouse":"W3","destination":[6,75]},{"id":"P6","warehouse":"W3","destination":[17,85]},{"id":"P7","warehouse":"W3","destination":[8,81]},{"id":"P8","warehouse":"W4","destination":[43,10]},{"id":"P9","warehouse":"W3","destination":[13,79]},{"id":"P10","warehouse":"W1","destination":[14,6]},{"id":"P11","warehouse":"W3","destination":[11,83]}]}"""
}

def execute_embedded_test_suite():
    print("")
    print("        LAUNCHING EMBEDDED EVALUATION ALL 10 TEST CASES             ")
    print("-------------------------------------------------------------------")
    
    master_report = []
    
    for case_id in sorted(TEST_CASES.keys(), key=int):
        print(f"[*] Processing Test Case {case_id} Execution Matrices...")
        raw_data = TEST_CASES[case_id]
        decoded = decode_string_manually(raw_data)
        cleaned = clean_and_normalize_schema(decoded)
        results = run_logistics_simulation(cleaned)
        
        formatted_json = serialize_to_json_string(results)
        print(f"\n[+] Verification Report Matrix for Test Case {case_id}:")
        print(formatted_json)
        print("-" * 68)
        
        master_report.append(f'"test_case_{case_id}": {formatted_json}')
        
    # Combine everything into one giant visible file structure
    combined_output = "{\n    " + ",\n    ".join(master_report) + "\n}"
    with open("report.json", "w", encoding="utf-8") as final_file:
        final_file.write(combined_output)
    print("\n[+] Success! Master file 'report.json' written with all 10 results.")



# 6. RUNTIME POINT



def main():
    if len(sys.argv) < 2 and not os.path.exists("data.json"):
        execute_embedded_test_suite()
        return

    input_filepath = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    if not os.path.exists(input_filepath):
        print(f"[-] Input file not found: '{input_filepath}'")
        return

    try:
        with open(input_filepath, "r", encoding="utf-8") as f:
            file_contents = f.read()
        parsed = decode_string_manually(file_contents)
        sanitized = clean_and_normalize_schema(parsed)
        simulation_output = run_logistics_simulation(sanitized)
        formatted_json_string = serialize_to_json_string(simulation_output)
        
        with open("report.json", "w", encoding="utf-8") as out_f:
            out_f.write(formatted_json_string)
        print(formatted_json_string)
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    main()