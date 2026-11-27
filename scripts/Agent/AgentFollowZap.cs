/*
name: Agent Follow Zap
description: Clears every monster on the room it stands in, joins the party it is invited to and accepts every summon, and stays until the campaign scheduler moves it or stops it. Stronger accounts run this while a weaker account works a story: the party summon puts them in the weak account's own room, which joining a map name never does. Spends nothing, free to play safe.
tags: agent, army, carry, zap, party, campaign
version: 0.4
*/
//cs_include Scripts/CoreBots.cs
//cs_include Scripts/Army/CoreArmyLite.cs
using Skua.Core.Interfaces;
using Skua.Core.Models.Monsters;

public class AgentFollowZap
{
    public IScriptInterface Bot => IScriptInterface.Instance;
    public CoreBots Core => CoreBots.Instance;

    // The library already knows how to answer a party invite and a party summon.
    // Reusing it is one line here and one less thing that can be wrong on a live account.
    // The library builds its helpers with a plain new and keeps one instance per
    // script run, which is what the army scripts do too.
    public CoreArmyLite Army = new CoreArmyLite();

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

        // A client only receives party invites with the party channel on.
        try
        {
            Bot.Send.Packet("%xt%zm%cmd%1%partyon%");
            Bot.Events.ExtensionPacketReceived += OnPacket;
            Core.Logger("ZAP|party-listener|on");
        }
        catch (Exception e)
        {
            Core.Logger($"ZAP|party-listener|failed|{e.GetType().Name}");
        }

        while (DateTime.Now < stop)
        {
            string map = MapName();
            if (map != lastMap)
            {
                Core.Logger($"ZAP|map|{map}|room {RoomId()}|players {Players()}|party {PartyLeader()}");
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
                Core.Logger($"ZAP|{map}|room {RoomId()}|attacks {attacks}|players {Players()}|party {PartyLeader()}");
                lastReport = DateTime.Now;
            }
        }

        try
        {
            Bot.Events.ExtensionPacketReceived -= OnPacket;
        }
        catch
        {
        }

        Core.Logger($"ZAP|stop|attacks {attacks}");
    }

    /// <summary>
    /// A party packet that throws must not take the story down with it, so the
    /// library handler runs inside a shell that keeps the room working.
    /// </summary>
    private void OnPacket(dynamic packet)
    {
        try
        {
            Army.PartyManagement(packet);
        }
        catch
        {
        }
    }

    private string PartyLeader()
    {
        try
        {
            string leader = Bot.Flash.GetGameObject<string>("world.partyOwner");
            return string.IsNullOrEmpty(leader) ? "none" : leader;
        }
        catch
        {
            return "?";
        }
    }

    private int RoomId()
    {
        try
        {
            return Bot.Map.RoomID;
        }
        catch
        {
            return 0;
        }
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
