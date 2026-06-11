from django.shortcuts import render
import requests
from .models import PlayerStats
 
# maybe i'll add an anti spam thing to deter assholes and losers
# deploy (clean up up code, files and purge DB), debug mode = False 
# add error logger 
# security

riot_api_key = 'RGAPI-df137e52-b767-43a1-9937-c3feb6c8a85e'

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

def format_champ_name(name):
    '''format champ image'''
    return name.replace(" ", "").replace("'", "")

def index(request):
    context = {}

    if request.method == 'POST':
        username = request.POST.get('userName')
        usertag = request.POST.get('userTag', '').lstrip('#')
        action = request.POST.get('action')

        # get the player id
        try:
            player_id_api = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{usertag}?api_key={riot_api_key}'
            response = requests.get(player_id_api)
            player_id_data = response.json()
            player_id = player_id_data['puuid']
        except Exception as e:
            return render(request, 'index.html', context={'error': 'player not found, please enter a correct username and tag combination'})

        # test 
        player_data = PlayerStats.objects.filter(puuid=player_id).first()
        if player_data and action != 'update':
            context = {
                'bestChamp': player_data.best_champ,
                'bestChampWinrate': player_data.best_champ_winrate,
                'champImgRoute': player_data.champ_img_route,

                'winkda': player_data.win_kda,
                'losekda': player_data.lose_kda,
                'kdatips': player_data.kda_tips,

                'jnglObjectives': player_data.jngl_objectives,
                'sortedJnglObjectives': player_data.sorted_jngl_objectives,

                'averageWardWins': player_data.average_ward_wins,
                'averageWardLoses': player_data.average_ward_loses,
                'wardingTips': player_data.warding_tips,

                'winByGameLength': player_data.win_by_game_length,
                'gameLengthTips': player_data.game_length_tips
            }

            return render(request, 'index.html', context)

        # get match ids 
        try:
            match_list_api = f'https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{player_id}/ids?start=0&count=20&api_key={riot_api_key}'
            response = requests.get(match_list_api)
            match_list = response.json()
            classic_matches_list = []
        except Exception as e:
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
                return render(request, 'index.html', context={'error': 'we are having problems with the API come back later'})
        
        if len(classic_matches_list) <= 1:
            return render(request, 'index.html', context={'error': 'not enough SUMMONERs RIFT games in your match history to gather information'})

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
        
        if best == None:
            return render(request, 'index.html', context={'error': 'not enough SUMMONERS RIFT games in your match history to gather information'})
        
        best_winrate = round(best_winrate * 100)


        # prepare url to get the champion icon
        champion_img = format_champ_name(best)
        version = '14.10.1'
        champion_img_route = f'https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champion_img}.png'

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



        # winrate by game length
        percentage_winrate_by_game_length = get_winrates(winrate_by_length)
        if percentage_winrate_by_game_length[0] > percentage_winrate_by_game_length[1]:
            game_length_tips = [
                'You perform better in short games',
                'After 25-30 min, avoid roaming the map aimlessly',
                'Convert leads into Baron / Elder, then eventually end the game.'
            ]
        else:
            game_length_tips = [
                'You perform better in long games',
                'Play safer in the early game and try to die less',
                'Play for the late game and focus on scaling',
            ]

        # winrate by jngl objectives ------------------------------------------------------
        obj_per = objectives_percentage(objectives_per_wins)
        obj_lose = objectives_percentage(objectives_per_loses)
        objective_names = ['drake', 'void grubs', 'rift', 'baron']
        paired_objectives = list(zip(objective_names, obj_per))
        sorted_paired_objectives = sorted(paired_objectives, key=lambda x:x[1], reverse=True)[0]
    
        # winrate by vision -------------------------------------------------------------
        ward_average = 0
        for ward in wards_per_minute_wins:
            ward_average += ward
        
        w_wins = round(ward_average / len(wards_per_minute_wins), 1)

        ward_average = 0
        for ward in wards_per_minute_loses:
            ward_average += ward
        
        w_loses = round(ward_average / len(wards_per_minute_loses), 1)


        
        if w_wins > w_loses:
            warding_tips = [
                'Higher vision in wins than loses',
                'your wins have much higher vision score than loses, focus on warding especially critical spots on the map and invest in control wards'
            ]
        
        else:
            warding_tips = [
                'Higher vision in losses than wins',
                'You are putting too much gold into wards sometimes its better to save that gold for items',
                'make sure to ward correctly, ward critical spots on the map'
            ]

        # wineate by kda ---------------------------------------------------------------------------------
        win_kda = calculate_kda_average(kda_per_wins)
        lose_kda = calculate_kda_average(kda_per_loses)

        if win_kda > lose_kda:
            kdatips = [
                'your KDA is highly impacting your wins',
                'focus on maintaining a good KDA',
                'do more proactive plays'
            ]
        else:
            kdatips = [
                'your good KDA is not affecting you wins',
                'dont be a KDA player'
                'dont be afraid of doing risky plays and dying as long as they help secure an advantage'
            ]
        
        # save data to DB 
        PlayerStats.objects.update_or_create(
        puuid=player_id,

        defaults={
            'best_champ': best,
            'best_champ_winrate': best_winrate,
            'champ_img_route': champion_img_route,

            'win_kda': win_kda,
            'lose_kda': lose_kda,

            'kda_tips': kdatips,

            'jngl_objectives': paired_objectives,
            'sorted_jngl_objectives': sorted_paired_objectives,

            'average_ward_wins': w_wins,
            'average_ward_loses': w_loses,

            'warding_tips': warding_tips,

            'win_by_game_length': percentage_winrate_by_game_length,
            'game_length_tips': game_length_tips
        }
    )
        # context -------------------------------------------------------------------------
        context = {
            'bestChamp': best,
            'bestChampWinrate':best_winrate,
            'champImgRoute':champion_img_route,
            'winkda':win_kda,
            'losekda':lose_kda,
            'kdatips':kdatips,
            'jnglObjectives':paired_objectives,
            'sortedJnglObjectives':sorted_paired_objectives,
            'averageWardWins':w_wins,
            'averageWardLoses':w_loses,
            'wardingTips':warding_tips,
            'winByGameLength':percentage_winrate_by_game_length,
            'gameLengthTips':game_length_tips
        }

    
    return render(request, 'index.html', context)
