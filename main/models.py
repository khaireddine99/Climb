from django.db import models

class PlayerStats(models.Model):
    puuid = models.CharField(max_length=200, unique=True)

    best_champ = models.CharField(max_length=50)
    best_champ_winrate = models.IntegerField()
    champ_img_route = models.TextField()

    win_kda = models.FloatField()
    lose_kda = models.FloatField()
    kda_tips = models.TextField()

    jngl_objectives = models.JSONField()
    sorted_jngl_objectives = models.JSONField()

    average_ward_wins = models.FloatField()
    average_ward_loses = models.FloatField()
    warding_tips = models.TextField()

    win_by_game_length = models.JSONField()
    game_length_tips = models.TextField()

    updated_at = models.DateTimeField(auto_now=True)