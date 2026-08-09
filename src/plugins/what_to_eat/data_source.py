"""随机美食推荐。"""

from dataclasses import dataclass
from random import choice


@dataclass(frozen=True)
class Food:
    """美食名称及人工挑选的 Wikimedia Commons 文件。"""

    name: str
    commons_file: str


FOODS = (
    Food("火锅", "File:Hot pot dinner.jpg"),
    Food("烤肉", "File:烤肉 (5904967326).jpg"),
    Food("麻辣烫", "File:Malatang from Hope Tree (20220226172344).jpg"),
    Food("冒菜", "File:传奇冒菜 1.jpg"),
    Food("串串香", "File:冷锅 串 Cold-pot Skewers Y1 per skewer (1495465364).jpg"),
    Food(
        "酸菜鱼",
        "File:酸菜鱼 Preserved Mustard Green with Fish - Charming Spice AUD24.80 (4104355401).jpg",
    ),
    Food("水煮肉片", "File:Shuizhu Roupian at Daqian Restaurant, Dachenglu (20260126131330).jpg"),
    Food("小炒肉", "File:Lajiao Chaorou at Xiangzhongyuan Hunan Cuisine, Beijing (20240131171407).jpg"),
    Food("番茄炒蛋", "File:Stir Fried Tomatoes with Scrambled Eggs.jpg"),
    Food("黄焖鸡米饭", "File:黄焖鸡米饭.jpg"),
    Food("咖喱饭", "File:日式咖喱饭.jpg"),
    Food("盖浇饭", "File:Rice with 3 toppings at a food court in Fangcaodi (20210923124853).jpg"),
    Food("炒饭", "File:Chinese fried rice.jpg"),
    Food("煲仔饭", "File:Claypot Chicken Rice, Singapore.JPG"),
    Food("牛肉面", "File:兰州牛肉面.jpg"),
    Food("重庆小面", "File:重庆小面 - 2024-05-25.jpg"),
    Food("炸酱面", "File:Zhajiangmian in Handan.jpg"),
    Food("螺蛳粉", "File:Luosifen at Guangya, Liuzhou (20190420141814).jpg"),
    Food("米线", "File:米线 Rice Noodles - 原味小吃 Yuanwei Xiaochi Y3.jpg"),
    Food("馄饨", "File:Wonton.jpg"),
    Food("饺子", "File:中国饺子（Jiaozi；Dumplings；餃子）.jpg"),
    Food("小笼包", "File:Xiao Long Bao by Junhao!.jpg"),
    Food("汉堡", "File:NCI Visuals Food Hamburger.jpg"),
    Food("披萨", "File:Vegetarian Pizza.jpg"),
    Food("炸鸡", "File:Fried-Chicken-Set.jpg"),
    Food("寿司", "File:Sushi platter, Nikko, Japan.jpg"),
    Food("烤鱼", "File:Grilled Fish with Douhua.jpg"),
    Food("烧烤", "File:Barbecue skewers.jpg"),
    Food("轻食沙拉", "File:Healthy Green Salad.JPG"),
    Food("自选菜", "File:Buffet dishes at Khua Din Restaurant.jpg"),
    Food("宫保鸡丁", "File:2016-08-14 Kung Pao Chicken dish in Beijing anagoria.jpg"),
    Food("鱼香肉丝", "File:川菜鱼香肉丝.jpg"),
    Food("回锅肉", "File:Twice cooked pork, Jia Yan, 5 rue Humblot, Paris 003.jpg"),
    Food("红烧肉", "File:Red braised pork belly.jpg"),
    Food("糖醋里脊", "File:Sweet-and-sour pork.jpg"),
    Food("北京烤鸭", "File:2016-08-27 Peking Duck at Great Wall Restaurant Beijing anagoria.jpg"),
    Food(
        "白切鸡",
        "File:HK SYP 西環 Sai Ying Pun 德輔道西 308 Des Voeux Road West 食神麗宮酒家 Chinese Banquet Seafood Restaurant food 海南 文昌 白切雞 Hainan Wenchang White Cut Chicken January 2026 N13P 03.jpg",
    ),
    Food("口水鸡", "File:Koushuiji.jpg"),
    Food("辣子鸡", "File:Làzijī (chicken with chilies).png"),
    Food("东坡肉", "File:Dongpo pork garnished.jpg"),
    Food("担担面", "File:Dandan Noodles.jpg"),
    Food("热干面", "File:Hot dry noodles.jpg"),
    Food("刀削面", "File:Datong Daoxiaomian.jpg"),
    Food("凉皮", "File:Liangpi.JPG"),
    Food("肉夹馍", "File:Xi'an roujiamo 05.jpg"),
    Food("煎饼果子", "File:Jianbing Guozi 20170610.jpg"),
    Food("生煎包", "File:Shengjian mantou.jpg"),
    Food("肠粉", "File:Dried shrimp rice noodle roll.jpg"),
    Food("炒河粉", "File:Dry Fried Beef Ho Fun - Ho Chiak 2023-12-08.jpg"),
    Food("海南鸡饭", "File:Home-cooked Hainanese chicken rice.jpg"),
    Food("石锅拌饭", "File:Bibimbap in stone bowl 비빔밥 (5534738694).jpg"),
    Food("越南河粉", "File:Bowl of Meatball pho.jpg"),
    Food("意大利面", "File:Spaghetti bolognese.jpg"),
    Food("牛排", "File:Steak-frites (steak-and-chips).jpg"),
    Food("三明治", "File:Classic Club Sandwich, Dôme East Fremantle, 2026 (02).jpg"),
    Food("墨西哥卷饼", "File:(20251114) Chicken burrito 01.jpg"),
    Food("冬阴功", "File:Tom Yum Koong Soup with Prawn and Straw Mushroom.jpg"),
    Food("烤羊肉串", "File:新疆羊肉串.jpg"),
    Food("烤冷面", "File:Grilled cold noodles (20241101).jpg"),
    Food("粥", "File:A Bowl of Congee in Tuen Mun.jpg"),
)


def recommend_food() -> Food:
    """随机选择一种美食。"""
    return choice(FOODS)
