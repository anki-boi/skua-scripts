/*
name: Agent Follow Zap
description: Clears every monster on the map it is standing on and stays there until the campaign scheduler moves it or stops it. Stronger accounts run this while a weaker account works a story, so the rooms die faster and the weaker account gets the kill credit. Spends nothing, free to play safe.
tags: agent, army, carry, zap, campaign
version: 0.3
*/
//cs_include Scripts/CoreBots.cs
using Skua.Core.Interfaces;
using Skua.Core.Models.Monsters;

public class AgentFollowZap
{
    public IScriptInterface Bot => IScriptInterface.Instance;
    public CoreBots Core => CoreBots.Instance;

    // The scheduler stops this script when the carried account no longer needs help.
    // Two hours is the safety net for a scheduler that died.
    private const int RunMinutes = 120;

    public void ScriptMain(IScriptInterface bot)
    {
        DateTime stop = DateTime.Now.AddMinutes(RunMinutes);
        string lastMap = "";
        DateTime lastReport = DateTime.Now;
        int attacks = 0;

        Core.Logger($"ZAP|start|{RunMinutes} minute cap");

        while (DateTime.Now < stop)
        {
            string map = MapName();
            if (map != lastMap)
            {
                Core.Logger($"ZAP|map|{map}|players {Players()}");
                lastMap = map;
                lastReport = DateTime.Now;
            }

            List<Monster> living = LivingMonsters();
            if (living.Count == 0)
            {
                System.Threading.Thread.Sleep(1500);
                continue;
            }

            foreach (Monster monster in living)
            {
                if (DateTime.Now >= stop)
                    break;
                try
                {
                    Bot.Combat.Attack(monster);
                    attacks++;
                }
                catch (Exception e)
                {
                    Core.Logger($"ZAP|attack failed|{monster?.Name}|{e.GetType().Name}");
                }
                System.Threading.Thread.Sleep(1200);
            }

            if (DateTime.Now - lastReport > TimeSpan.FromMinutes(2))
            {
                Core.Logger($"ZAP|{map}|attacks {attacks}|players {Players()}");
                lastReport = DateTime.Now;
            }
        }

        Core.Logger($"ZAP|stop|attacks {attacks}");
    }

    private List<Monster> LivingMonsters()
    {
        List<Monster> living = new();
        try
        {
            foreach (Monster monster in Bot.Monsters.CurrentMonsters ?? new List<Monster>())
            {
                if (monster != null && monster.Alive)
                    living.Add(monster);
            }
        }
        catch (Exception e)
        {
            Core.Logger($"ZAP|monster list failed|{e.GetType().Name}");
        }
        return living;
    }

    private string MapName()
    {
        try
        {
            return Bot.Map.Name ?? "?";
        }
        catch
        {
            return "?";
        }
    }

    private int Players()
    {
        try
        {
            return Bot.Map.PlayerCount;
        }
        catch
        {
            return 0;
        }
    }
}
