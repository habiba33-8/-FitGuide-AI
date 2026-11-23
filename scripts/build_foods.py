"""Builds backend/fitguide/data/foods.json from a compact table.
Values are per 100 g of the food AS EATEN (cooked where it says cooked).
They are rounded reference values compiled from common public nutrition tables
(USDA-style values for global foods; typical recipe-based estimates for Egyptian
dishes). They are estimates, not lab measurements. See docs/EVALUATION.md.
Columns: id, name, arabic, category, kcal, protein, carbs, fat, portion_g, portion_label, aliases
"""
import json, pathlib
F = [
# Egyptian / Middle Eastern
("koshary","Koshari","كشري","egyptian",150,4.5,27,2.8,350,"1 medium plate",["kushari","koshary","kosheri"]),
("ful_medames","Ful medames","فول مدمس","egyptian",110,7,14,3,200,"1 plate",["foul","fava beans","ful"]),
("taameya","Ta'ameya (falafel)","طعمية","egyptian",330,13,32,17,35,"1 piece",["falafel","tamiya","taamiya"]),
("aish_baladi","Baladi bread","عيش بلدي","egyptian",260,9,53,1.5,90,"1 loaf",["baladi bread","eish baladi","aish baladi","pita bread"]),
("molokhia","Molokhia (cooked, with broth)","ملوخية","egyptian",55,4,6,1.5,200,"1 bowl",["mulukhiyah","jute mallow"]),
("mahshi","Mahshi (stuffed vegetables)","محشي","egyptian",150,3,25,4,60,"1 piece",["stuffed vine leaves","warak enab","stuffed zucchini"]),
("egyptian_rice","Egyptian rice with vermicelli","رز مصري","egyptian",170,3.2,31,3.5,180,"1 cup",["rice with vermicelli","white rice egyptian"]),
("fattah","Fattah","فتة","egyptian",230,11,24,10,300,"1 plate",["fatta"]),
("shakshuka","Shakshuka","شكشوكة","egyptian",110,6,6,7,250,"1 pan",["eggs in tomato sauce"]),
("fried_eggs","Fried egg","بيض مقلي","egyptian",196,13.6,0.8,15,50,"1 egg",["egg fried"]),
("boiled_egg","Boiled egg","بيض مسلوق","protein",155,12.6,1.1,10.6,50,"1 egg",["egg","hard boiled egg","eggs"]),
("beid_omelette","Omelette (2 eggs)","أومليت","egyptian",154,11,0.6,12,120,"1 omelette",["omelet"]),
("feteer","Feteer meshaltet (plain)","فطير مشلتت","egyptian",420,8,45,23,200,"1 piece",["feteer","fiteer"]),
("hawawshi","Hawawshi","حواوشي","egyptian",290,14,26,14,250,"1 loaf",["hawawshy"]),
("kebda","Liver, pan-fried (kebda)","كبدة","egyptian",165,26,4,5,150,"1 serving",["liver","beef liver"]),
("shawarma_chicken","Chicken shawarma sandwich","شاورما فراخ","egyptian",225,14,22,9,250,"1 sandwich",["shawarma","chicken shawarma"]),
("kofta","Kofta (grilled)","كفتة","egyptian",250,17,3,19,120,"4 pieces",["kofta","kebab kofta"]),
("kahk","Kahk (plain)","كحك","egyptian",470,6,55,25,30,"1 piece",["kahk","eid cookies"]),
("basbousa","Basbousa","بسبوسة","egyptian",380,4,58,15,80,"1 piece",["basbousa","namoura"]),
("om_ali","Om Ali","أم علي","egyptian",260,6,30,13,200,"1 bowl",["umm ali"]),
("roz_bel_laban","Rice pudding","رز بلبن","egyptian",130,3.5,22,3,200,"1 cup",["rice pudding"]),
("tahini","Tahini","طحينة","egyptian",595,17,21,54,15,"1 tbsp",["tahina"]),
("hummus","Hummus","حمص","egyptian",166,8,14,10,60,"1/4 cup",["hommos","chickpea dip"]),
("baba_ghanoush","Baba ghanoush","بابا غنوج","egyptian",120,2.5,8,9,60,"1/4 cup",["baba ganoush"]),
("feta_cheese","Feta cheese","جبنة فيتا","dairy",264,14,4,21,30,"1 slice",["white cheese","gebna beyda","feta"]),
("roumi_cheese","Roumi cheese","جبنة رومي","dairy",390,26,2,31,30,"1 slice",["rumi cheese"]),
("labneh","Labneh","لبنة","dairy",170,7,5,13,30,"2 tbsp",["strained yogurt"]),
("dates","Dates","بلح","fruit",282,2.5,75,0.4,24,"1 date",["date","medjool"]),
("sweet_potato","Sweet potato (baked)","بطاطا","carb",90,2,21,0.2,150,"1 medium",["batata"]),
# staples & grains
("white_rice","White rice (cooked)","رز أبيض","carb",130,2.7,28,0.3,180,"1 cup",["rice"]),
("brown_rice","Brown rice (cooked)","رز بني","carb",123,2.7,26,1,180,"1 cup",["brown rice"]),
("pasta","Pasta (cooked)","مكرونة","carb",158,5.8,31,0.9,200,"1 plate",["spaghetti","macaroni","penne"]),
("oats","Oats (dry)","شوفان","carb",389,17,66,7,40,"1/2 cup dry",["oatmeal","rolled oats"]),
("bread_white","White bread","عيش توست","carb",265,9,49,3.2,30,"1 slice",["toast","sandwich bread"]),
("bread_whole","Whole wheat bread","عيش أسمر","carb",247,13,41,3.4,30,"1 slice",["brown bread","wholemeal bread"]),
("potato_boiled","Potato (boiled)","بطاطس مسلوقة","carb",87,1.9,20,0.1,150,"1 medium",["boiled potato"]),
("french_fries","French fries","بطاطس مقلية","carb",312,3.4,41,15,120,"1 portion",["fries","chips"]),
("quinoa","Quinoa (cooked)","كينوا","carb",120,4.4,21,1.9,185,"1 cup",["quinoa"]),
("couscous","Couscous (cooked)","كسكسي","carb",112,3.8,23,0.2,157,"1 cup",["couscous"]),
("corn_cooked","Corn (boiled)","ذرة","carb",96,3.4,21,1.5,150,"1 cob",["sweet corn","corn on the cob"]),
("cornflakes","Cornflakes","كورن فليكس","carb",357,7.5,84,0.4,30,"1 cup",["cereal"]),
# protein
("chicken_breast_grilled","Chicken breast (grilled)","صدور فراخ مشوية","protein",165,31,0,3.6,120,"1 breast",["chicken breast","grilled chicken","فراخ"]),
("chicken_thigh","Chicken thigh (roasted, skin on)","وراك فراخ","protein",229,24,0,14,100,"1 thigh",["chicken thigh","roasted chicken"]),
("fried_chicken","Fried chicken","فراخ مقلية","protein",290,24,10,17,120,"1 piece",["crispy chicken","broasted"]),
("beef_steak","Beef steak (grilled)","استيك","protein",271,25,0,19,150,"1 steak",["steak","beef"]),
("ground_beef","Ground beef (cooked, 15% fat)","لحمة مفرومة","protein",250,26,0,15,100,"1 serving",["minced meat","burger patty"]),
("lamb","Lamb (roasted)","ضاني","protein",294,25,0,21,120,"1 serving",["mutton","lamb"]),
("tuna_canned","Tuna (canned in water)","تونة","protein",116,26,0,1,120,"1 can",["tuna"]),
("salmon","Salmon (baked)","سلمون","protein",206,22,0,12,150,"1 fillet",["salmon"]),
("white_fish","White fish (grilled)","سمك مشوي","protein",120,22,0,3,150,"1 fillet",["tilapia","sea bass","fish","bolti"]),
("shrimp","Shrimp (cooked)","جمبري","protein",99,24,0.2,0.3,100,"1 serving",["prawns","shrimp"]),
("lentils_cooked","Lentils (cooked)","عدس","protein",116,9,20,0.4,200,"1 bowl",["lentil soup","adas"]),
("chickpeas_cooked","Chickpeas (cooked)","حمص حب","protein",164,8.9,27,2.6,150,"3/4 cup",["chickpeas","garbanzo"]),
("white_beans","White beans (cooked)","فاصوليا بيضاء","protein",139,9.7,25,0.5,170,"1 cup",["beans"]),
("tofu","Tofu","توفو","protein",76,8,1.9,4.8,100,"1 serving",["tofu"]),
("whey_protein","Whey protein shake (1 scoop in water)","بروتين واي","protein",120,24,3,1.5,30,"1 scoop",["protein shake","whey"]),
# dairy
("milk_whole","Milk (whole)","لبن كامل الدسم","dairy",61,3.2,4.8,3.3,250,"1 glass",["milk"]),
("milk_skim","Milk (skim)","لبن خالي الدسم","dairy",34,3.4,5,0.1,250,"1 glass",["skim milk","low fat milk"]),
("yogurt_plain","Plain yogurt (whole)","زبادي","dairy",61,3.5,4.7,3.3,170,"1 cup",["yoghurt","zabadi"]),
("greek_yogurt","Greek yogurt (plain, low fat)","زبادي يوناني","dairy",73,10,3.9,1.9,170,"1 cup",["greek yoghurt"]),
("cottage_cheese","Cottage cheese","جبنة قريش","dairy",98,11,3.4,4.3,100,"1/2 cup",["areesh","قريش"]),
("cheddar","Cheddar cheese","جبنة شيدر","dairy",403,25,1.3,33,28,"1 slice",["cheese"]),
("butter","Butter","زبدة","fat",717,0.9,0.1,81,10,"1 tbsp",["butter"]),
# fats / nuts
("olive_oil","Olive oil","زيت زيتون","fat",884,0,0,100,14,"1 tbsp",["oil","cooking oil"]),
("peanut_butter","Peanut butter","زبدة فول سوداني","fat",588,25,20,50,16,"1 tbsp",["pb"]),
("almonds","Almonds","لوز","fat",579,21,22,50,28,"1 handful",["almond"]),
("walnuts","Walnuts","عين جمل","fat",654,15,14,65,28,"1 handful",["walnut"]),
("peanuts","Peanuts","فول سوداني","fat",567,26,16,49,28,"1 handful",["peanut"]),
("avocado","Avocado","أفوكادو","fat",160,2,9,15,150,"1 fruit",["avocado"]),
# vegetables
("salad_green","Green salad (no dressing)","سلطة خضراء","veg",20,1.2,3.5,0.2,150,"1 bowl",["salad","lettuce salad"]),
("tomato_cucumber_salad","Tomato and cucumber salad (with oil)","سلطة طماطم وخيار","veg",45,1,6,2.2,150,"1 bowl",["egyptian salad","salata baladi"]),
("tomato","Tomato","طماطم","veg",18,0.9,3.9,0.2,120,"1 medium",["tomatoes"]),
("cucumber","Cucumber","خيار","veg",15,0.7,3.6,0.1,100,"1 medium",["cucumbers"]),
("carrot","Carrot","جزر","veg",41,0.9,10,0.2,70,"1 medium",["carrots"]),
("broccoli","Broccoli (steamed)","بروكلي","veg",35,2.4,7,0.4,100,"1 cup",["broccoli"]),
("spinach_cooked","Spinach (cooked)","سبانخ","veg",23,3,3.8,0.3,100,"1 cup",["spinach"]),
("zucchini_cooked","Zucchini (cooked)","كوسة","veg",17,1.1,3.1,0.3,120,"1 cup",["courgette"]),
("eggplant_fried","Eggplant (fried)","باذنجان مقلي","veg",200,1.5,10,17,100,"1 serving",["fried aubergine"]),
("okra_stew","Okra stew (bamia)","بامية","egyptian",70,2.5,8,3,250,"1 plate",["bamia","okra"]),
("mixed_vegetables_cooked","Mixed vegetables (cooked)","خضار مطبوخ","veg",60,2.5,9,2,200,"1 plate",["vegetable stew","khodar"]),
# fruit
("apple","Apple","تفاح","fruit",52,0.3,14,0.2,180,"1 medium",["apples"]),
("banana","Banana","موز","fruit",89,1.1,23,0.3,118,"1 medium",["bananas"]),
("orange","Orange","برتقال","fruit",47,0.9,12,0.1,130,"1 medium",["oranges"]),
("mango","Mango","مانجا","fruit",60,0.8,15,0.4,200,"1 cup",["mango"]),
("grapes","Grapes","عنب","fruit",69,0.7,18,0.2,150,"1 cup",["grape"]),
("watermelon","Watermelon","بطيخ","fruit",30,0.6,7.6,0.2,280,"1 slice",["watermelon"]),
("strawberries","Strawberries","فراولة","fruit",32,0.7,7.7,0.3,150,"1 cup",["strawberry"]),
("pomegranate","Pomegranate","رمان","fruit",83,1.7,19,1.2,150,"1/2 fruit",["pomegranate"]),
# fast food / snacks / drinks
("burger_beef","Cheeseburger","برجر","fastfood",260,14,28,10,200,"1 burger",["hamburger","burger"]),
("pizza_cheese","Pizza (cheese)","بيتزا","fastfood",266,11,33,10,110,"1 slice",["pizza slice"]),
("sandwich_cheese","Cheese sandwich (white bread)","ساندوتش جبنة","fastfood",290,12,30,13,130,"1 sandwich",["cheese sandwich"]),
("chips_crisps","Potato chips","شيبسي","snack",536,7,53,34,30,"1 small bag",["crisps","chipsy"]),
("chocolate_milk","Milk chocolate","شوكولاتة","snack",535,7.7,59,30,40,"1 bar",["chocolate"]),
("biscuit","Biscuit / cookie","بسكويت","snack",480,6,70,20,25,"2 pieces",["cookie","biscuits"]),
("ice_cream","Ice cream","آيس كريم","snack",207,3.5,24,11,100,"1 scoop",["gelato"]),
("juice_orange","Orange juice","عصير برتقال","drink",45,0.7,10,0.2,250,"1 glass",["juice"]),
("soda","Soft drink (cola)","مشروب غازي","drink",42,0,10.6,0,330,"1 can",["cola","pepsi","coke"]),
("tea_sugar","Tea with 2 tsp sugar","شاي بسكر","drink",32,0,8,0,200,"1 cup",["shay","tea with sugar"]),
("coffee_black","Black coffee","قهوة سادة","drink",2,0.3,0,0,200,"1 cup",["coffee","americano"]),
("latte","Latte (whole milk)","لاتيه","drink",55,3,5,2.8,300,"1 cup",["cafe latte","coffee with milk"]),
("water","Water","مياه","drink",0,0,0,0,250,"1 glass",["water"]),
]
out=[]
for r in F:
    i,n,a,c,k,p,cb,f,pg,pl,al=r
    out.append(dict(id=i,name=n,arabic=a,category=c,per100g=dict(kcal=k,protein=p,carbs=cb,fat=f),portion_g=pg,portion_label=pl,aliases=al))
ids=[o["id"] for o in out]; assert len(ids)==len(set(ids)),[i for i in ids if ids.count(i)>1]
# sanity: macros should roughly explain calories (within 25%) except water/coffee/alcohol-free low cal
for o in out:
    m=o["per100g"]; est=m["protein"]*4+m["carbs"]*4+m["fat"]*9
    if m["kcal"]>40 and abs(est-m["kcal"])/m["kcal"]>0.25: print("CHECK",o["id"],m["kcal"],round(est))
pathlib.Path(__file__).resolve().parents[1].joinpath("backend/fitguide/data/foods.json").write_text(json.dumps(out,ensure_ascii=False,indent=1))
print(len(out),"foods")
