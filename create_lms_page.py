# TODO:
#  Create template to match current LMS page contents with vars and string manip
#  Collect list of all pages that still need creating
#  Get item name and query chisel (https://chisel.weirdgloop.org/moid/item_name.html) to get object data, or query wiki with non-LMS name to get stats
#  Collect all items and their data and populate a template, written out to rs_wiki/ppage_outputs/<item_name>.wikitext

from dataclasses import dataclass, asdict, replace
from datetime import datetime
from pprint import pprint, pformat
from pprint import PrettyPrinter
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from osrsreboxed import items_api
from osrsreboxed.items_api.item_properties import ItemProperties
from osrsreboxed.items_api.all_items import AllItems


class CustomPrettyPrinter(PrettyPrinter):
  def __init__(self, *args, exclude_attr=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.exclude_attr = exclude_attr

  def format(self, obj, context, maxlevels, level):
    # Check if the object is a dataclass instance
    # if hasattr(obj, '__dataclass_fields__'):  # the "obj" is always the value, not the dataclass obj
    if isinstance(obj, str) and len(obj) > 100:
      # Convert to dictionary and exclude the specified attribute
      filtered_dict = {}
      return super().format(filtered_dict, context, maxlevels, level)
    return super().format(obj, context, maxlevels, level)


exclude_icon = "icon"
pprinter = CustomPrettyPrinter(exclude_attr=exclude_icon)


@dataclass
class LmsItem:
  '''Intermediary object to hold LMS item data before creating new ItemProperties object.'''
  buy_limit: Optional[int]
  cost: int
  highalch: int
  id: int
  linked_id_noted: Optional[int]
  linked_id_placeholder: Optional[int]
  lowalch: int
  members: bool
  noteable: bool
  tradeable: Optional[bool]
  tradeable_on_ge: bool


def print_only_attr(obj: ItemProperties | list[ItemProperties], attr: str):
  if isinstance(obj, list):
    pprint(get_only_attr(obj, attr))
  else:
    print(get_only_attr(obj, attr))


def get_only_attr(obj: ItemProperties | list[ItemProperties], attr: str):
  if isinstance(obj, list):
    return sorted([getattr(item, attr) for item in obj])
  else:
    return getattr(obj, attr)


def get_all_matching_items(items: AllItems, lms_item_names: list[str]) -> list[ItemProperties]:
  '''Get list of all items with name match to lms_item_names list'''
  lms_items = [x for x in items if x.name in lms_item_names]
  print("Number of lms items returned: ", len(lms_items))
  print_only_attr(lms_items, "name")
  pprinter.pprint(lms_items)
  return lms_items


def compare_items_by_id(id1: int, id2: int, items: AllItems):
  item1 = items.lookup_by_item_id(id1)
  item2 = items.lookup_by_item_id(id2)
  dict1 = asdict(item1)
  dict2 = asdict(item2)
  differences = {key: (dict1[key], dict2[key])
                 for key in dict1 if dict1[key] != dict2[key]}
  pprinter.pprint(differences)


def compare_items(item1: ItemProperties, item2: ItemProperties, items: AllItems):
  dict1 = asdict(item1)
  dict2 = asdict(item2)
  differences = {key: (dict1[key], dict2[key])
                 for key in dict1 if dict1[key] != dict2[key]}
  pprinter.pprint(differences)


def create_lms_item(original_item: ItemProperties, lms_item: LmsItem) -> ItemProperties:
  '''Create a new LMS variant of an item, given an existing ItemProperties obj.'''
  # create separate case for ghostly robe as both top and bottom item.names are "Ghostly robe"
  if "Ghostly robe" in original_item.wiki_name:
    lms_object = replace(original_item,
                         name=original_item.wiki_name,
                         wiki_name=original_item.wiki_name + " (Last Man Standing)",
                         # Split and remove any subsections from the wiki_url, e.g. Dragon_knife#Unpoisoned -> Dragon_knife
                         wiki_url=original_item.wiki_url.split("#", 1)[0] + "_(Last_Man_Standing)",
                         **asdict(lms_item)
                        )
    
  lms_object = replace(original_item,
                       wiki_name=original_item.wiki_name + " (Last Man Standing)",
                       # Split and remove any subsections from the wiki_url, e.g. Dragon_knife#Unpoisoned -> Dragon_knife
                       wiki_url=original_item.wiki_url.split("#", 1)[0] + "_(Last_Man_Standing)",
                       **asdict(lms_item)
                       )
  return lms_object


def convert_date_format(date_str):
  # Convert the string to a datetime object
  date_obj = datetime.strptime(date_str, '%Y-%m-%d')

  # Format the datetime object to the desired format
  formatted_date = date_obj.strftime('[[%d %B]] [[%Y]]').lstrip("0").replace("[0", "[")
  return formatted_date


def create_template(item: ItemProperties):
  '''Create wikitext page by populating lms_wikitext_template.wikitext.j2 template.
  Created files will be created at ./page_outputs/{item_name}.wikitext'''
  env = Environment(loader=FileSystemLoader('./templates'))
  template = env.get_template('lms_wikitext_template.wikitext.j2')
  item_dict = asdict(item)

  # check if weapon, create attack range key/value
  if item.weapon:
    item_range = 0
    if item.weapon.weapon_type in ["2h_sword", "axe", "blaster", "bludgeon", "blunt", "claw", "pickaxe", "polearm", "polestaff", "powered staff", "scythe", "slash_sword", "spear", "spiked", "stab sword", "whip"]:
      item_range = 1
    if item.weapon.weapon_type in ["bow", "crossbow"]:
      item_range = 9
    if item.weapon.weapon_type == "thrown":
      item_range = 4
    if item.weapon.weapon_type == "staff":
      item_range = "staff"
    item_dict["attack_range"] = item_range

  # update item.release_date for wikitext formatting
  # check if release_date is older than 4 August 2016, if so, replace release date with 4 August 2016, as that is the date LMS released
  if item.release_date < "2016-08-04":
    print(f"{item.release_date} is before 4 August 2016")
    item_dict["release_date"] = "2016-08-04"
  item_dict["release_date"] = convert_date_format(item_dict["release_date"])
    
  # set the item options: "Wield, Drop" if a weapon, "Wear, Drop" if armor
  if item.equipable_weapon:
    item_dict["options"] = "Wield, Drop"
  else:
    item_dict["options"] = "Wear, Drop"

  output = template.render(item=item_dict)
  with open(f"./page_outputs/{item.wiki_name}.wikitext", "w") as f:
    f.write(output)


lms_item_names = [
    # Loot table
    "Armadyl crossbow",
    "Armadyl godsword",
    "Ancient godsword",
    "Dark bow",
    "Dragon arrow",
    "Dragon claws",
    "Dragon javelin",
    "Elder maul",
    "Ghrazi rapier",
    "Granite maul",
    "Heavy ballista",
    "Infernal cape",
    "Inquisitor's mace",
    "Kodai wand",
    "Mage's book",
    "Occult necklace",
    "Opal dragon bolts (e)",
    "Seers ring (i)",
    "Staff of the dead",
    "Zaryte crossbow",
    "Volatile nightmare staff",
    "Ahrim's robetop",
    "Ahrim's robeskirt",
    "Amulet of fury",
    "Ancestral hat",
    "Ancestral robe top",
    "Ancestral robe bottom",
    "Bandos tassets",
    "Blessed spirit shield",
    "Dharok's helm",
    "Dharok's platebody",
    "Dharok's platelegs",
    "Dharok's greataxe",
    "Eternal boots",
    "Guthan's helm",
    "Karil's leathertop",
    "Mithril seeds",
    "Torag's helm",
    "Torag's platelegs",
    "Verac's helm",
    "Verac's brassard",
    "Verac's plateskirt",
    "Verac's flail",
    "Lightbearer",
    "Morrigan's javelin",
    "Statius's warhammer",
    "Vesta's longsword",
    "Voidwaker",
    "Zuriel's staff",
    "Atlatl dart",
    "Blue moon spear",
    "Eclipse atlatl",
    "Dual macuahuitl",
    "3rd age range top",
    "3rd age range legs",
    "3rd age range coif",
    "3rd age robe top",
    "3rd age robe",
    "3rd age mage hat",
    "Amulet of torture",
    "Fremennik kilt",
    "Infinity boots",
    "Inquisitor's great helm",
    "Inquisitor's hauberk",
    "Inquisitor's plateskirt",
    "Mithril seeds",
    "Necklace of anguish",
    "Tormented bracelet",
    "Blood moon helm",
    "Blood moon chestplate",
    "Blood moon tassets",
    "Blue moon helm",
    "Blue moon chestplate",
    "Blue moon tassets",
    "Eclipse moon helm",
    "Eclipse moon chestplate",
    "Eclipse moon tassets",
    "Dragon knife",
    "Light ballista",
    "Blessed dragonhide chaps",
    "Elder chaos hood",
    "Elder chaos top",
    "Elder chaos robe",
    "Ancient halo",
    "Armadyl halo",
    "Bandos halo",
    "Brassica halo",
    "Guthix halo",
    "Saradomin halo",
    "Seren halo",
    "Zamorak halo",
    "Rangers' tunic",
    "Spiked macles",
    "Wizard boots",
    ##### Stock items #####
    # helm slot
    "Helm of neitiznot",
    "Berserker helm",
    "Ghostly hood",
    # cape slot
    "Imbued guthix cape",
    "Imbued saradomin cape",
    "Imbued zamorak cape",
    # ammy slot
    "Amulet of glory",
    "Occult necklace",
    # ammo slot
    "Diamond bolts (e)",
    # weapon slot
    "Abyssal whip",
    "Ahrim's staff",
    "Ancient staff",
    "Dragon dagger",
    "Dragon scimitar",
    "Rune crossbow",
    # body slot
    "Black d'hide body",
    "Ghostly robe (top)",
    "Mystic robe top",
    "Mystic robe top (dark)",
    "Mystic robe top (light)",
    # offhand slot
    "Dragon defender",
    "Rune defender",
    "Spirit shield",
    "Tome of fire",
    "Unholy book",
    # leg slot
    "Black d'hide chaps",
    "Ghostly robe (bottom)",
    "Mystic robe bottom",
    "Mystic robe bottom (dark)",
    "Mystic robe bottom (light)",
    "Rune platelegs",
    # glove slot
    "Barrows gloves",
    "Mithril gloves",
    # boot slot
    "Climbing boots",
    # ring slot
    "Berserker ring"
]

# all items will have a `wiki_name` equal to the item name plus (Last Man Standing)
# and same for `wiki_url`
lms_items_without_wiki_page = {
    '3rd age mage hat': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 27183,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    '3rd age range coif': {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27201,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    '3rd age range legs': {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27200,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    '3rd age range top': {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27199,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    '3rd age robe': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 20577,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    '3rd age robe top': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 20576,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Amulet of torture': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27173,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ancestral robe top': {
        'buy_limit': None,
        'cost': 55,
        'highalch': 0,
        'id': 27193,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ancient godsword': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 27184,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ancient staff': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 20431,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Berserker helm': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27169,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Black d'hide chaps": {
        'buy_limit': None,
        'cost': 30,
        'highalch': 0,
        'id': 20424,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Dragon knife': {
        'buy_limit': None,
        'cost': 5,
        'highalch': 0,
        'id': 27157,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Dragon scimitar': {
        'buy_limit': None,
        'cost': 30,
        'highalch': 0,
        'id': 20406,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Elder chaos hood': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27176,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Elder chaos robe': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27175,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Elder chaos top': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27174,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Fremennik kilt': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27177,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ghostly hood': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27166,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ghostly robe (bottom)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27168,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Ghostly robe (top)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27167,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Guthix chaps': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27180,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Guthix halo': {
        'buy_limit': None,
        'cost': 5,
        'highalch': 0,
        'id': 27163,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Infinity boots': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27170,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Inquisitor's great helm": {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27195,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Inquisitor's hauberk": {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27196,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Inquisitor's mace": {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27198,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Inquisitor's plateskirt": {
        'buy_limit': None,
        'cost': 20,
        'highalch': 0,
        'id': 27197,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Mithril gloves': {
        'buy_limit': None,
        'cost': 350,  # not sure MOID is correct here
        'highalch': 0,
        'id': 20581,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Mystic robe bottom (dark)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27159,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Mystic robe bottom (light)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27161,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Mystic robe top (dark)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27158,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Mystic robe top (light)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27160,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Necklace of anguish': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27172,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Opal dragon bolts (e)': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27192,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    "Rangers' tunic": {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27179,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Rune defender': {
        'buy_limit': None,
        'cost': 3,
        'highalch': 0,
        'id': 27185,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Saradomin chaps': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27182,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Saradomin halo': {
        'buy_limit': None,
        'cost': 5,
        'highalch': 0,
        'id': 27165,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Spiked manacles': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27178,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Tome of fire': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27358,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Tormented bracelet': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27171,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Unholy book': {
        'buy_limit': None,
        'cost': 1,
        'highalch': 0,
        'id': 27191,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Wizard boots': {
        'buy_limit': None,
        'cost': 5,
        'highalch': 0,
        'id': 27162,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Zamorak chaps': {
        'buy_limit': None,
        'cost': 10,
        'highalch': 0,
        'id': 27181,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Zamorak halo': {
        'buy_limit': None,
        'cost': 5,
        'highalch': 0,
        'id': 27164,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    },
    'Zaryte crossbow': {
        'buy_limit': None,
        'cost': 40,
        'highalch': 0,
        'id': 27186,
        'linked_id_noted': 0,
        'linked_id_placeholder': None,
        'lowalch': 0,
        'members': False,
        'noteable': True,
        'tradeable': False,  # double check this
        'tradeable_on_ge': False
    }
}

items = items_api.load()

# compare_items(23605, 21795, items)  # imbued zammy cape
# compare_items(9243, 23649, items)   # diamond bolts (e)
# compare_items(7462, 23593, items)   # barrows gloves

# pprinter.pprint(items.lookup_by_item_name('Spiked manacles'))

# cut this list down to only the normal version of each item and store in lms_items
# get_all_matching_items(items, lms_item_names)
# pprinter.pprint(items.lookup_by_item_name("Dragon knife"))

# Get list of all existing wiki pages for LMS items
lms_wiki_pages = [x for x in items if getattr(x, "wiki_name", "") and
                  "Last Man Standing" in getattr(x, "wiki_name", "") and
                  x.duplicate == False]
print("Number of lms items with wiki pages: ", len(lms_wiki_pages))
# pprinter.pprint(lms_wiki_pages)
# print_only_attr(lms_wiki_pages, "name")

# store missing_lms_wiki_pages as a dict above, lms_items_without_wiki_page
lms_item_names_with_wiki_pages = get_only_attr(lms_wiki_pages, "name")
missing_lms_wiki_pages = sorted([item for item in lms_item_names if item not in lms_item_names_with_wiki_pages])
# print("Number of lms items without wiki pages: ", len(missing_lms_wiki_pages))
# print("lms items without wiki pages:\n", pformat(missing_lms_wiki_pages))

for name, data in lms_items_without_wiki_page.items():
  print(name)
  temp = LmsItem(**data)
  
  # enable wiki name for ghostly robe top because of name collision with ghostly robe bottoms
  # TODO: investigate why this isn't creating two separate page files
  if name in ["Ghostly robe (top)", "Ghostly robe (bottom)"]:
    original_item = items.lookup_by_item_name(name, True)
  else:
    original_item = items.lookup_by_item_name(name)
  lms_item = create_lms_item(original_item, temp)
  create_template(lms_item)
