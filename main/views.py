from django.shortcuts import render
import requests
import time 
from concurrent.futures import ThreadPoolExecutor
 
# add bar to monitor elo (simple info bar, username and elo) 
# save all to database, first search calls from DB if it exists, UPDATE button calls the riot API
# optimize performance 
# test cases
# security (obscure admin adress, anti bots)

riot_api_key = 'RGAPI-8fa5edc7-2088-44a8-a60a-ce90cb048ae9'

def get_winrates(data):
    '''cleans up winrate by game length data'''
    early = data.get('early', {})
    late = data.get('late', {})

    early_total = early.get('win', 0) + early.get('lose', 0)
    late_total = late.get('win', 0) + late.get('lose', 0)

    win_early = (early.get('win', 0) / early_total * 100) if early_total > 0 else 0
    win_late = (late.get('win', 0) / late_total * 100) if late_total > 0 else 0

    return round(win_early, 1), round(win_late, 1)

def objectives_percentage(data):
    '''calculates objectives percentage'''
    sums_ally = [0, 0, 0, 0]
    sums_total = [0, 0, 0, 0]

    for ally, total in data:
        for i in range(4):
            sums_ally[i] += ally[i]
            sums_total[i] += total[i]

    percentages = []
    for i in range(4):
        if sums_total[i] == 0:
            percentages.append(0)
        else:
            percentages.append(round((sums_ally[i] / sums_total[i]) * 100, 1))

    return percentages

def calculate_kda_average(kda):
    '''calculates average KDA from a list'''
    total = 0
    for k in kda:
        total += k

    final_kda = round(total / len(kda), 1)
    return final_kda

def fetch_match(match_id):
    url = f'https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={riot_api_key}'
    
def index(request):
    context = {}

    if request.method == 'POST':
        username = request.POST.get('userName')
        usertag = request.POST.get('userTag', '').lstrip('#')

        # get the player id
        try:
            player_id_api = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{usertag}?api_key={riot_api_key}'
            response = requests.get(player_id_api)
            player_id_data = response.json()
            player_id = player_id_data['puuid']
            print(f"player id {player_id_data['puuid']}")
        except Exception as e:
            return render(request, 'index.html', context={'error': 'player not found, please enter correct username and tag'})
            
        # get match ids 
        try:
            match_list_api = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{player_id}/ids?start=0&count=20&api_key={riot_api_key}'
            response = requests.get(match_list_api)
            match_list = response.json()
            classic_matches_list = []
        except Exception as e:
            print(f'failed at retrieving the matches')
            return render(request, 'index.html', context={'error': 'we are having problems with the API come back later'})

        # get each match info and store the CLASSIC only games 
        for m in match_list:
            try:
                match_info_api = f'https://europe.api.riotgames.com/lol/match/v5/matches/{m}?api_key={riot_api_key}'
                response = requests.get(match_info_api)
                data = response.json()
                if data['info']['gameMode'] == 'CLASSIC':
                    classic_matches_list.append(data)
            except Exception as e:
                print('failed at retrieving match info')
                return render(request, 'index.html', context={'error': 'we are having problems with the API come back later'})
        
        if len(classic_matches_list) <= 1:
            return render(request, 'index.html', context={'error': 'not enough SUMMONER RIFT games in your histroy to gather information'})

        # store champions in disctionnary, calculate winrate
        favorite_heroes = {}

        for match in classic_matches_list:
            for player in match['info']['participants']:
                if player['puuid'] == player_id:
                    champ = player['championName']
                    win = player['win']

                    if champ not in favorite_heroes:
                        favorite_heroes[champ] = {
                            "games": 0,
                            "wins": 0,
                            "losses": 0
                        }

                    favorite_heroes[champ]["games"] += 1

                    if win:
                        favorite_heroes[champ]["wins"] += 1
                    else:
                        favorite_heroes[champ]["losses"] += 1
        
        best = None
        best_winrate = -1

        # best champ selection 
        for champ, stats in favorite_heroes.items():
            if stats['games'] > 1:
                winrate = stats['wins'] / stats['games']
                
                if winrate > best_winrate:
                    best_winrate = winrate 
                    best = champ
        
        best_winrate = round(best_winrate * 100)

        winrate_by_length = {
            'early': {
                'win':0,
                'lose':0
            },
            'late':{
                'win':0,
                'lose':0
            }
        }

        wards_per_minute_wins = []
        wards_per_minute_loses = []

        objectives_per_wins = []
        objectives_per_loses = []

        kda_per_wins = []
        kda_per_loses = []
        
        # game length, winrate by game length 
        for match in classic_matches_list:
            # detect game result for player 
            for player in match['info']['participants']:
                if player['puuid'] == player_id:
                    win = player['win']
                    vision_score = player['visionScore']
                    kills = player['kills']
                    deaths = player['deaths']
                    assists = player['assists']
                    team_id = player['teamId']

            duration_seconds = match['info']['gameDuration']
            minutes = duration_seconds // 60
            wards_per_minute = vision_score / minutes

            if minutes < 30:
                if win:
                    winrate_by_length['early']['win'] += 1
                else:
                    winrate_by_length['early']['lose'] += 1
            else:
                if win:
                    winrate_by_length['late']['win'] += 1
                else:
                    winrate_by_length['late']['lose'] += 1
            
            if win:
                wards_per_minute_wins.append(wards_per_minute)
            else:
                wards_per_minute_loses.append(wards_per_minute)

            # calculate kda
            kda = round((kills + assists) / max(1, deaths), 1)
            if win:
                kda_per_wins.append(kda)
            else:
                kda_per_loses.append(kda)

            # get jngl objective data
            ally_objectives = [0, 0, 0, 0]
            total_objectives = [0, 0, 0, 0]

            teams = match['info']['teams']

            for team in teams:
                dragons = team["objectives"]["dragon"]["kills"]
                void_grubs = team["objectives"]["horde"]["kills"]
                riftHerald = team["objectives"]["riftHerald"]["kills"]
                baron = team["objectives"]["baron"]["kills"]

                # Add to TOTAL (both teams)
                total_objectives[0] += dragons
                total_objectives[1] += void_grubs
                total_objectives[2] += riftHerald
                total_objectives[3] += baron

                # Store ALLY only
                if team['teamId'] == team_id:
                    ally_objectives = [dragons, void_grubs, riftHerald, baron]
            
            if win:
                objectives_per_wins.append([ally_objectives, total_objectives])
            else:
                objectives_per_loses.append([ally_objectives, total_objectives])

        print(f'based on your match history your best performing champion is {best}')

        # winrate by game length
        percentage_winrate_by_game_length = get_winrates(winrate_by_length)
        if percentage_winrate_by_game_length[0] > percentage_winrate_by_game_length[1]:
            game_length_tips = [
                'strong early, weak late',
                'You win more early games—focus on ending faster',
                'Avoid unnecessary fights after 25–30 min',
                'Convet leads into baron / elder and eventually ending the game'
            ]
        else:
            game_length_tips = [
                'weak early, strong late',
                'Play safer in the early game and try to die less',
                'Focus on farming / clearing camps / scaling',
                'Avoid unnecessary fights'
            ]

        # winrate by jngl objectives 
        obj_per = objectives_percentage(objectives_per_wins)
        obj_lose = objectives_percentage(objectives_per_loses)
        objective_names = ['dragon', 'void grubs', 'rift', 'baron']
        paired_objectives = list(zip(objective_names, obj_per))
        paired_objectives = sorted(paired_objectives, key=lambda x:x[1], reverse=True)
    
        # winrate by vision -------------------------------------------------------------
        ward_average = 0
        for ward in wards_per_minute_wins:
            ward_average += ward
        
        w_wins = round(ward_average / len(wards_per_minute_wins), 1)

        ward_average = 0
        for ward in wards_per_minute_loses:
            ward_average += ward
        
        w_loses = round(ward_average / len(wards_per_minute_loses), 1)

        print(f'ward win {w_wins}, ward loses {w_loses}')
        
        if w_wins > w_loses:
            warding_tips = [
                'Higher vision in wins than loses',
                'your wins have much higher wins than loses, focus on warding,\nbuying control wards,\nwarding jngl objectives'
            ]
        
        else:
            warding_tips = [
                'Higher vision in losses',
                'You are putting too much gold into wards \nYou are not warding critical spots on the map'
            ]

        # wineate by kda ---------------------------------------------------------------------------------
        win_kda = calculate_kda_average(kda_per_wins)
        lose_kda = calculate_kda_average(kda_per_loses)
        print(f'kda average while win {win_kda}')
        print(f'kda average while losing {lose_kda}')

        if win_kda > lose_kda:
            print(f'your KDA is highly impacting your wins \n focus on dying less \n do more pro active plays')
        else:
            print(f'your KDA is not affecting you wins \n dont be afraid of doing risky plays and dying as long as they help secure objectives ')

        # context -------------------------------------------------------------------------
        context = {
            'bestChamp': best,
            'bestChampWinrate':best_winrate,
            'gameLength':game_length_tips,
            'objectives':paired_objectives,
            'vision':warding_tips
        }
    
    return render(request, 'index.html', context)
