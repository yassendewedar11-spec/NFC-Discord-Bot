const {
  Client,
  GatewayIntentBits,
  PermissionsBitField,
  SlashCommandBuilder,
  REST,
  Routes
} = require("discord.js");

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

const commands = [
  new SlashCommandBuilder()
    .setName("hello")
    .setDescription("Say hello"),

  new SlashCommandBuilder()
    .setName("clear")
    .setDescription("Delete messages")
    .addIntegerOption(option =>
      option.setName("amount")
        .setDescription("Number of messages to delete")
        .setRequired(true)
        .setMinValue(1)
        .setMaxValue(100)
    ),

  new SlashCommandBuilder()
    .setName("kick")
    .setDescription("Kick a member")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member to kick")
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName("reason")
        .setDescription("Reason")
    ),

  new SlashCommandBuilder()
    .setName("ban")
    .setDescription("Ban a member")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member to ban")
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName("reason")
        .setDescription("Reason")
    ),

  new SlashCommandBuilder()
    .setName("warn")
    .setDescription("Warn a member")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member to warn")
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName("reason")
        .setDescription("Reason")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("warnings")
    .setDescription("View a member's warnings")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("timeout")
    .setDescription("Timeout a member")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member to timeout")
        .setRequired(true)
    )
    .addIntegerOption(option =>
      option.setName("minutes")
        .setDescription("Timeout duration in minutes")
        .setRequired(true)
        .setMinValue(1)
        .setMaxValue(40320)
    ),

  new SlashCommandBuilder()
    .setName("untimeout")
    .setDescription("Remove a member's timeout")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("ticket")
    .setDescription("Create a support ticket"),

  new SlashCommandBuilder()
    .setName("close")
    .setDescription("Close the current ticket"),

  new SlashCommandBuilder()
    .setName("promote")
    .setDescription("Promote a member")
    .addUserOption(option =>
      option.setName("user")
        .setDescription("Member to promote")
        .setRequired(true)
    ),

  new SlashCommandBuilder()
    .setName("ticket_dashboard")
    .setDescription("Show the ticket dashboard")
].map(command => command.toJSON());

const warnings = new Map();

client.once("ready", async () => {
  console.log(`Logged in as ${client.user.tag}`);

  const rest = new REST({ version: "10" })
    .setToken(process.env.TOKEN);

  try {
    console.log("Registering slash commands...");

    await rest.put(
      Routes.applicationCommands(client.user.id),
      { body: commands }
    );

    console.log("Slash commands registered successfully.");
  } catch (error) {
    console.error("Slash command registration failed:", error);
  }
});

client.on("messageCreate", async message => {
  if (message.author.bot) return;
  if (!message.content.startsWith("!")) return;

  const args = message.content.slice(1).trim().split(/\s+/);
  const command = args.shift()?.toLowerCase();

  if (command === "hello") {
    return message.reply("Hello! 👋");
  }

  if (command === "clear") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)) {
      return message.reply("❌ You need Manage Messages permission.");
    }

    const amount = parseInt(args[0]);

    if (!amount || amount < 1 || amount > 100) {
      return message.reply("❌ Choose a number between 1 and 100.");
    }

    await message.channel.bulkDelete(amount, true);
    return;
  }

  if (command === "kick") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.KickMembers)) {
      return message.reply("❌ You need Kick Members permission.");
    }

    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    if (!member.kickable) {
      return message.reply("❌ I can't kick that member.");
    }

    await member.kick(args.slice(1).join(" ") || "No reason provided.");
    return message.reply(`✅ Kicked ${member.user.tag}.`);
  }

  if (command === "ban") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.BanMembers)) {
      return message.reply("❌ You need Ban Members permission.");
    }

    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    if (!member.bannable) {
      return message.reply("❌ I can't ban that member.");
    }

    await member.ban({
      reason: args.slice(1).join(" ") || "No reason provided."
    });

    return message.reply(`✅ Banned ${member.user.tag}.`);
  }

  if (command === "warn") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.ModerateMembers)) {
      return message.reply("❌ You need Moderate Members permission.");
    }

    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    const reason = args.slice(1).join(" ") || "No reason provided.";

    if (!warnings.has(member.id)) {
      warnings.set(member.id, []);
    }

    warnings.get(member.id).push({
      reason,
      moderator: message.author.tag,
      date: new Date().toISOString()
    });

    return message.reply(`⚠️ ${member.user.tag} has been warned.`);
  }

  if (command === "warnings") {
    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    const list = warnings.get(member.id) || [];

    if (list.length === 0) {
      return message.reply(`✅ ${member.user.tag} has no warnings.`);
    }

    const text = list
      .map((w, i) => `**${i + 1}.** ${w.reason} — ${w.moderator}`)
      .join("\n");

    return message.reply(`⚠️ Warnings for ${member.user.tag}:\n${text}`);
  }

  if (command === "timeout") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.ModerateMembers)) {
      return message.reply("❌ You need Moderate Members permission.");
    }

    const member = message.mentions.members.first();
    const minutes = parseInt(args[1]);

    if (!member || !minutes) {
      return message.reply("❌ Usage: `!timeout @user 10`");
    }

    if (!member.moderatable) {
      return message.reply("❌ I can't timeout that member.");
    }

    await member.timeout(minutes * 60 * 1000);

    return message.reply(`🔇 ${member.user.tag} timed out for ${minutes} minutes.`);
  }

  if (command === "untimeout") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.ModerateMembers)) {
      return message.reply("❌ You need Moderate Members permission.");
    }

    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    await member.timeout(null);

    return message.reply(`🔊 ${member.user.tag} is no longer timed out.`);
  }

  if (command === "promote") {
    if (!message.member.permissions.has(PermissionsBitField.Flags.ManageRoles)) {
      return message.reply("❌ You need Manage Roles permission.");
    }

    const member = message.mentions.members.first();

    if (!member) {
      return message.reply("❌ Mention a member.");
    }

    return message.reply(
      `✅ Promotion command received for ${member.user.tag}.\nRole setup will be added next.`
    );
  }

  if (command === "ticket") {
    return message.reply("🎫 Ticket system will be added next.");
  }

  if (command === "close") {
    return message.reply("🔒 Ticket closing system will be added next.");
  }

  if (command === "ticket_dashboard") {
    return message.reply("🎫 Ticket dashboard will be added next.");
  }
});

client.on("interactionCreate", async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const { commandName } = interaction;

  if (commandName === "hello") {
    return interaction.reply("Hello! 👋");
  }

  if (commandName === "clear") {
    if (!interaction.memberPermissions.has(PermissionsBitField.Flags.ManageMessages)) {
      return interaction.reply({
        content: "❌ You need Manage Messages permission.",
        ephemeral: true
      });
    }

    const amount = interaction.options.getInteger("amount");

    await interaction.channel.bulkDelete(amount, true);

    return interaction.reply({
      content: `🧹 Deleted ${amount} messages.`,
      ephemeral: true
    });
  }

  if (commandName === "kick") {
    if (!interaction.memberPermissions.has(PermissionsBitField.Flags.KickMembers)) {
      return interaction.reply({
        content: "❌ You need Kick Members permission.",
        ephemeral: true
      });
    }

    const user = interaction.options.getUser("user");
    const member = await interaction.guild.members.fetch(user.id);
    const reason = interaction.options.getString("reason") || "No reason provided.";

    if (!member.kickable) {
      return interaction.reply({
        content: "❌ I can't kick that member.",
        ephemeral: true
      });
    }

    await member.kick(reason);

    return interaction.reply(`✅ Kicked ${user.tag}.`);
  }

  if (commandName === "ban") {
    if (!interaction.memberPermissions.has(PermissionsBitField.Flags.BanMembers)) {
      return interaction.reply({
        content: "❌ You need Ban Members permission.",
        ephemeral: true
      });
    }

    const user = interaction.options.getUser("user");
    const member = await interaction.guild.members.fetch(user.id);
    const reason = interaction.options.getString("reason") || "No reason provided.";

    if (!member.bannable) {
      return interaction.reply({
        content: "❌ I can't ban that member.",
        ephemeral: true
      });
    }

    await member.ban({ reason });

    return interaction.reply(`✅ Banned ${user.tag}.`);
  }

  if (commandName === "warn") {
    const user = interaction.options.getUser("user");
    const reason = interaction.options.getString("reason");

    if (!warnings.has(user.id)) {
      warnings.set(user.id, []);
    }

    warnings.get(user.id).push({
      reason,
      moderator: interaction.user.tag,
      date: new Date().toISOString()
    });

    return interaction.reply(`⚠️ ${user.tag} has been warned.`);
  }

  if (commandName === "warnings") {
    const user = interaction.options.getUser("user");
    const list = warnings.get(user.id) || [];

    if (list.length === 0) {
      return interaction.reply(`✅ ${user.tag} has no warnings.`);
    }

    const text = list
      .map((w, i) => `**${i + 1}.** ${w.reason} — ${w.moderator}`)
      .join("\n");

    return interaction.reply(`⚠️ Warnings for ${user.tag}:\n${text}`);
  }

  if (commandName === "timeout") {
    const user = interaction.options.getUser("user");
    const minutes = interaction.options.getInteger("minutes");
    const member = await interaction.guild.members.fetch(user.id);

    if (!member.moderatable) {
      return interaction.reply({
        content: "❌ I can't timeout that member.",
        ephemeral: true
      });
    }

    await member.timeout(minutes * 60 * 1000);

    return interaction.reply(
      `🔇 ${user.tag} timed out for ${minutes} minutes.`
    );
  }

  if (commandName === "untimeout") {
    const user = interaction.options.getUser("user");
    const member = await interaction.guild.members.fetch(user.id);

    await member.timeout(null);

    return interaction.reply(`🔊 ${user.tag} is no longer timed out.`);
  }

  if (commandName === "promote") {
    const user = interaction.options.getUser("user");

    return interaction.reply(
      `✅ Promotion command received for ${user.tag}.\nRole setup will be added next.`
    );
  }

  if (commandName === "ticket") {
    return interaction.reply("🎫 Ticket system will be added next.");
  }

  if (commandName === "close") {
    return interaction.reply("🔒 Ticket closing system will be added next.");
  }

  if (commandName === "ticket_dashboard") {
    return interaction.reply("🎫 Ticket dashboard will be added next.");
  }
});

client.login(process.env.TOKEN);
