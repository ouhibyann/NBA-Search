import sys
import requests
from datetime import date
from bs4 import BeautifulSoup, Comment
from difflib import SequenceMatcher
from modules.objects import Team, Player
from data.text_data import alltime_player_list

base_url = "https://www.basketball-reference.com"
adv_stat_map = {
    "true shooting percentage" : "ts_pct",
	"total rebound percentage" : "trb_pct",
	"defensive plus/minus" : "dbpm",
	"offensive plus/minus" : "obpm",
	"player efficiency rating" : "per",
	"assist percentage" : "ast_pct" 
}

"""
Function to get a map of current playoff 
scores

Parameters
----------
n/a

Returns
-------
bracket_map : dict
    A mapping of the NBA playoff bracket
"""
def get_playoff_bracket():
    year = int(date.today().year)
    url = "{}/playoffs/NBA_{}.html".format(base_url, str(year))
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    table = page_content.findAll("tr")
    bracket_map = {
        "Western Conference First Round" : [],
        "Eastern Conference First Round" : [],
        "Western Conference Semifinals" : [],
        "Eastern Conference Semifinals" : [],
        "Western Conference Finals" : [],
        "Eastern Conference Finals" : [],
        "Finals" : []
    }

    for row in table:
        td_list = row.findAll("td")
        a_list = row.findAll("a")
        level = None
        if td_list:
            for t in td_list:
                if t.string in bracket_map:
                    level = t.string
        
        if level:
            team1 = a_list[0].string
            team2 = a_list[1].string
            curr_score = a_list[1].next_sibling.string
            score1 = curr_score[3]
            score2 = curr_score[5]
            cell = [(team1, str(score1)), (team2, str(score2))]
            bracket_map[level].append(cell)

    return bracket_map
    


"""
Function to get a list of player names
from specific year

Parameters
----------
year : int
    The year to scrape for NBA player
    names

Returns
-------
player_list : list
    The list of player names
"""
def get_player_names(year):
    url = "{}/leagues/NBA_{}_per_game.html".format(base_url, str(year))
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    table = page_content.findAll("tr",attrs={"class":"full_table"})
    names = []
    for row in table:
        name = row.find("a").string
        names.append(name)
    return names


"""
Function to get a list of player objects 
with player stats

Parameters
----------
table : bs4.element.ResultSet
    BeautifulSoup object with player stats

Returns
-------
player_list : list
    The list of player objects with scraped stats
"""
def get_stat_list(table):
    player_list = []
    for row in table:
        name = row.find("a").string
        player = Player(name)
        attr = {}
        stats = row.findAll("td")
        for stat in stats:
            attr[stat["data-stat"]] = stat.string
        player.create(attr)
        player_list.append(player)
    return player_list

"""
Function to get current NBA standings in
the east, west, or entire NBA.

Parameters
----------
conf : str
    The requested conference standings

Returns
-------
standings : list
    The ranked list of teams to signify standings
"""
def get_standings(conf):
    resp = requests.get(base_url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    table = page_content.findAll("tr",attrs={"class":"full_table"})

    # Iterate over ranking table in website HTML 
    standings = []
    for i,row in enumerate(table):
        team = row.find("a")["title"]
        wins = row.find("td",attrs={"data-stat":"wins"}).string
        losses = row.find("td",attrs={"data-stat":"losses"}).string
        t = Team(team, wins, losses, i%15+1)
        standings.append(t)
    
    # Return rankings based on conference 
    switch = {
        "all" : standings,
        "east": standings[:15],
        "west": standings[15:]
    }

    return switch.get(conf, "Invalid Conference")

"""
Function to get the player efficiency
rating for all NBA players in a specific
year

Parameters
----------
year : int
    The year to scrape for NBA player
    efficiency rating

Returns
-------
per_list : list
    The list of tuples with player name and PER
"""
def get_per(year):
    url = "{}/leagues/NBA_{}_advanced.html".format(base_url, str(year))
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    table = page_content.findAll("tr",attrs={"class":"full_table"})
    per_list = []
    for row in table:
        name = row.find("a").string
        
        per = 0.0
        stats = row.findAll("td")
        for stat in stats:
            if stat["data-stat"] == "per":
                per = float(stat.string)
        per_list.append((name, per))
    return per_list

"""
Function to get the advanced statistic
for NBA player career

Parameters
----------
player : int
    NBA player for stat retrieval
stat : string
    statistic to return

Returns
-------
stat_list : list
    The list of tuples with player name and PER
"""
def get_adv_stat(name, stat):
    max_similarity = lambda a, b : a if a[1] > b[1] else b
    similar_name = (None, 0.0)
    for player in alltime_player_list:
        ratio = SequenceMatcher(None, name, player).ratio()
        curr_name = (player, ratio)
        similar_name = max_similarity(similar_name, curr_name)

    target_name = similar_name[0]
    ln_initial = target_name.split()[-1][0].lower()
    url = "{}/players/{}/".format(base_url, ln_initial)
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    th = page_content.findAll("th")
    for row in th:
        a = row.find("a")
        if a and a.string == target_name:
            url = base_url + a["href"]
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    advanced_div = page_content.find("div",attrs={"id":"all_advanced"})
    comments = advanced_div.find_all(string=lambda text: isinstance(text, Comment))[0]
    stat_html = str(comments)
    stat_soup = BeautifulSoup(stat_html, "html.parser")
    stat_tag = adv_stat_map[stat]
    stat_td = stat_soup.find("td", attrs={"data-stat":stat_tag})
    return float(stat_td.string) if stat_td else 0.0

"""
Function to get NBA players stats
for a specific year

Parameters
----------
year : int
    The year to scrape for NBA player
    stats

Returns
-------
get_player_list(table) : list
    The list of player objects with scraped stats
"""
def get_player_stats(year):
    url = "{}/leagues/NBA_{}_per_game.html".format(base_url, str(year))
    resp = requests.get(url)
    page_content = BeautifulSoup(resp.content, "html.parser")
    table = page_content.findAll("tr",attrs={"class":"full_table"})
    return get_stat_list(table)