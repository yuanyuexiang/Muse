"""Demo：用一份样例 MenuSpec 渲染成印刷 PDF。

    docker compose exec backend python -m app.menu.demo /app/data/menu_demo.pdf
"""

import sys

from app.menu.render import render_menu_pdf
from app.schemas import Dish, MenuCategory, MenuSpec, SetMeal, ShopInfo


def sample() -> MenuSpec:
    return MenuSpec(
        shop=ShopInfo(
            name="ORIENTAL CHEF",
            tagline="Chinese Food to Take Away",
            phone="01622 791 368",
            address="6 Premier Parade, Aylesford, Maidstone, Kent, ME20 7LN",
            online_order_url="orientalchefaylesford.com",
            opening_hours=["周一–周四 16:45–22:00", "周五/周六 16:45–22:30", "周二休息"],
            delivery_terms=["外送起送 £18.00", "满 £25 送虾片", "满 £60 送虾片 + 软饮"],
            promotions=["满 £25 免费虾片", "满 £60 送虾片和软饮"],
            allergen_notice="14 种过敏原提示：如对花生/麸质/海鲜等过敏，请点餐时告知。",
        ),
        categories=[
            MenuCategory(name="Appetizer 前菜", dishes=[
                Dish(number="1", name="Mixed Hors d'oeuvres", description="每位 · 最少两位起", price="£6.00"),
                Dish(number="2", name="Seaweed", price="£5.70", flags=["vegetarian"]),
                Dish(number="4", name="Mini Vegetarian Spring Rolls (8)", price="£4.30", flags=["vegetarian"]),
                Dish(number="6", name="Satay Chicken on Skewers (4)", price="£5.20", flags=["nut"]),
                Dish(number="8", name="Chicken Wings, Salt & Chilli", price="£7.20", flags=["hot"]),
                Dish(number="9", name="Crispy Aromatic Duck (1/4)", price="£13.00"),
            ]),
            MenuCategory(name="Soups 汤", dishes=[
                Dish(number="11", name="Chicken & Mushroom Soup", price="£4.00"),
                Dish(number="12", name="Chicken & Noodle Soup", price="£4.00"),
                Dish(number="14", name="Hot & Sour Soup", price="£4.20", flags=["hot"]),
            ]),
            MenuCategory(name="Curry 咖喱", dishes=[
                Dish(number="41", name="House Special Curry", price="£8.00", flags=["hot"]),
                Dish(number="44", name="Beef Curry", price="£7.80", flags=["hot"]),
                Dish(number="47", name="Mixed Vegetable Curry", price="£6.80", flags=["hot", "vegetarian"]),
            ]),
            MenuCategory(name="Chow Mein 炒面", dishes=[
                Dish(number="31", name="House Special Chow Mein (Large)", price="£9.00"),
                Dish(number="34", name="Beef Chow Mein", price="£6.60"),
                Dish(number="40", name="Plain Chow Mein", price="£5.80", flags=["vegetarian"]),
            ]),
            MenuCategory(name="Chicken 鸡", dishes=[
                Dish(number="60", name="Chicken & Mushrooms", price="£8.00"),
                Dish(number="62", name="Chicken w/ Green Peppers, Black Bean Sauce", price="£8.00", flags=["hot"]),
                Dish(number="69", name="Chicken w/ Ginger & Spring Onion", price="£8.00"),
            ]),
            MenuCategory(name="Beef 牛", dishes=[
                Dish(number="72", name="Beef & Mushrooms", price="£8.40"),
                Dish(number="76", name="Beef in Chilli Sauce", price="£8.40", flags=["hot"]),
                Dish(number="79", name="Beef with Oyster Sauce", price="£8.40"),
            ]),
            MenuCategory(name="Vegetables 蔬菜", dishes=[
                Dish(number="V1", name="Stir Fried Beansprouts", price="£5.30", flags=["vegetarian"]),
                Dish(number="V5", name="Mushroom with Satay Sauce", price="£7.00", flags=["vegetarian", "nut"]),
                Dish(number="V10", name="Stir Fried Broccoli", price="£6.20", flags=["vegetarian"]),
            ]),
        ],
        set_meals=[
            SetMeal(name="Set Meal for 1", price="£12.00",
                    items=["Chicken Chop Suey", "Sweet & Sour Pork Balls", "Egg Fried Rice"]),
            SetMeal(name="Set A · for 2", price="£27.50",
                    items=["Spring Rolls", "Chicken w/ Mushrooms", "King Prawn Chop Suey", "Egg Fried Rice"]),
            SetMeal(name="Set C · for 3", price="£44.00",
                    items=["Crispy Aromatic Duck", "Beef w/ Green Peppers", "S&S Chicken HK", "Special Fried Rice"]),
        ],
    )


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/data/menu_demo.pdf"
    data = render_menu_pdf(sample())
    with open(out, "wb") as f:
        f.write(data)
    print(f"wrote {out} ({len(data)} bytes)")
