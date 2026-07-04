# run_concierge.py
import asyncio
import subprocess
import json
import sys

async def main():
    # Launch your custom local database process directly
    proc = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("\n🟢 Nutrition Concierge Local Loop Running!")
    print("===============================================================")
    print("Available options: 'log meal', 'take supplement', 'summary', 'adjust', or 'exit'")

    while True:
        action = input("\nWhat would you like to do? ").strip().lower()
        if action in ["exit", "quit"]:
            break
            
        if action == "log meal":
            food = input("What did you eat? ").strip()
            cals = input("Calories (kcal)? ").strip()
            prot = input("Protein (g)? ").strip()
            carbs = input("Carbohydrates (g)? ").strip()
            sugar = input("Sugar (g)? ").strip()
            water = input("Water (oz)? ").strip()
            
            req = {
                "method": "call_tool",
                "params": {
                    "name": "write_food_macros",
                    "arguments": {
                        "food_item": food,
                        "calories": cals,
                        "protein": prot,
                        "carbs": carbs,
                        "sugar": sugar,
                        "water_oz": water
                    }
                }
            }
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            
            res_line = proc.stdout.readline()
            res = json.loads(res_line)
            if "error" in res:
                err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                print(f"❌ Error: {err_msg}")
            else:
                print(res.get("result"))
            
        elif action == "take supplement":
            print("Options: 'adult multivitamin', 'fish oil', 'apple cider vinegar', 'd3', 'joint health'")
            supp = input("Which one did you take? ").strip()
            
            req = {"method": "call_tool", "params": {"name": "update_supplement_checklist", "arguments": {"supplement_name": supp}}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            
            res_line = proc.stdout.readline()
            res = json.loads(res_line)
            if "error" in res:
                err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                print(f"❌ Error: {err_msg}")
            else:
                print(res.get("result"))
            
        elif action == "summary":
            req = {"method": "call_tool", "params": {"name": "query_local_diary_db", "arguments": {}}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            
            res_line = proc.stdout.readline()
            res = json.loads(res_line)
            if "error" in res:
                err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                print(f"❌ Error: {err_msg}")
            else:
                data = res.get("result", {})
                date_str = data.get("date", "N/A")
                day_of_week = data.get("day_of_week", "N/A")
                print(f"\n--- TODAY'S TOTAL BUDGET ({day_of_week}, {date_str}) ---")
                print(f"🔥 Calories: {data.get('calories', 0)} kcal")
                print(f"🍗 Protein: {data.get('protein', 0)}g")
                print(f"🌾 Carbohydrates: {data.get('carbohydrates', 0)}g")
                print(f"🍬 Sugar: {data.get('sugar', 0)}g")
                
                water_drank = data.get('water', 0)
                water_status = "✅ Met Goal" if water_drank >= 128 else f"❌ {128 - water_drank} oz remaining"
                print(f"💧 Water: {water_drank}/128 oz ({water_status})")
                
                print(f"💊 Supplements Checklist:")
                for k, v in data.get('checklist', {}).items():
                    print(f"  - {k.title()}: {v}")
                    
        elif action == "adjust":
            req = {"method": "call_tool", "params": {"name": "query_local_diary_db", "arguments": {}}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            
            res_line = proc.stdout.readline()
            res = json.loads(res_line)
            if "error" in res:
                err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                print(f"❌ Error: {err_msg}")
            else:
                data = res.get("result", {})
                entries = data.get("entries", [])
                
                print("\n--- Today's Entries ---")
                if not entries:
                    print("No food/water entries logged today.")
                else:
                    for entry in entries:
                        print(f"ID: {entry['id']} | {entry['food_item']} (🔥 {entry['calories']} kcal, 🍗 {entry['protein']}g protein, 🌾 {entry['carbs']}g carbs, 🍬 {entry['sugar']}g sugar, 💧 {entry['water_oz']} oz water)")
                
                print("\nSupplements:")
                for k, v in data.get("checklist", {}).items():
                    print(f"  - {k.title()}: {v}")
                
                target_type = input("\nWould you like to adjust a 'food' entry, a 'supplement' status, or 'cancel'? ").strip().lower()
                if target_type == "food":
                    if not entries:
                        print("No entries to adjust.")
                    else:
                        try:
                            target_id = int(input("Enter the ID of the food/water entry to delete: ").strip())
                            req = {"method": "call_tool", "params": {"name": "delete_food_entry", "arguments": {"id": target_id}}}
                            proc.stdin.write(json.dumps(req) + "\n")
                            proc.stdin.flush()
                            
                            res_line = proc.stdout.readline()
                            res = json.loads(res_line)
                            if "error" in res:
                                err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                                print(f"❌ Error: {err_msg}")
                            else:
                                print(f"✅ {res.get('result')}")
                        except ValueError:
                            print("❌ Error: Invalid ID entered.")
                elif target_type == "supplement":
                    print("Options: 'adult multivitamin', 'fish oil', 'apple cider vinegar', 'd3', 'joint health'")
                    supp = input("Which one would you like to adjust? ").strip().lower()
                    status = input("Mark as 'taken' or 'missing'? ").strip().lower()
                    if status not in ["taken", "missing"]:
                        print("❌ Error: Invalid status (must be 'taken' or 'missing').")
                    else:
                        is_taken = 1 if status == "taken" else 0
                        req = {"method": "call_tool", "params": {"name": "update_supplement_checklist", "arguments": {"supplement_name": supp, "is_taken": is_taken}}}
                        proc.stdin.write(json.dumps(req) + "\n")
                        proc.stdin.flush()
                        
                        res_line = proc.stdout.readline()
                        res = json.loads(res_line)
                        if "error" in res:
                            err_msg = res["error"].get("message") if isinstance(res["error"], dict) else res["error"]
                            print(f"❌ Error: {err_msg}")
                        else:
                            print(f"✅ {res.get('result')}")

    proc.terminate()

if __name__ == "__main__":
    asyncio.run(main())