/*
name: Agent Free Dailies
description: Runs the free-to-play dailies one by one, skips what this account cannot do, and logs every result.
tags: agent, dailies, free, f2p
version: 0.1
*/
//cs_include Scripts/CoreBots.cs
//cs_include Scripts/CoreFarms.cs
//cs_include Scripts/CoreDailies.cs
//cs_include Scripts/CoreStory.cs
//cs_include Scripts/CoreAdvanced.cs
//cs_include Scripts/Dailies/MineCrafting.cs
using System;
using System.Collections.Generic;
using Skua.Core.Interfaces;
using Skua.Core.Options;

public class AgentFreeDailies
{
    private IScriptInterface Bot => IScriptInterface.Instance;
    private CoreBots Core => CoreBots.Instance;
    private CoreDailies Daily = new CoreDailies();
    private MineCrafting Mining = new MineCrafting();

    public string OptionsStorage = "AgentFreeDailies";
    public bool DontPreconfigure = true;

    public List<IOption> Options = new()
    {
        CoreBots.Instance.SkipOptions,
    };

    public void ScriptMain(IScriptInterface bot)
    {
        Core.SetOptions();

        Core.Logger($"AgentFreeDailies start | {bot.Player.Username} lv{bot.Player.Level} member={bot.Player.IsMember}");

        Run("SparrowsBlood", () => Daily.SparrowsBlood());
        Run("EldersBlood", () => Daily.EldersBlood());
        Run("ShadowShroud", () => Daily.ShadowShroud());
        Run("DagesScrollFragment", () => Daily.DagesScrollFragment());
        Run("CollectorClass", () => Daily.CollectorClass());
        Run("PowerGem", () => Daily.PowerGem());
        Run("CryptoToken", () => Daily.CryptoToken());
        Run("WheelofDoom", () => Daily.WheelofDoom());
        Run("MineCrafting", () => Mining.DoMinecrafting());

        Core.Logger("AgentFreeDailies finished");

        Core.SetOptions(false);
    }

    /// <summary>One daily, logged, so a daily this account cannot do does not end the run.</summary>
    private void Run(string name, Action step)
    {
        if (Bot.ShouldExit)
            return;

        try
        {
            Core.Logger($"DAILY|{name}|start");
            step();
            Core.Logger($"DAILY|{name}|done");
        }
        catch (Exception e)
        {
            Core.Logger($"DAILY|{name}|skipped: {e.Message}");
        }
    }
}
