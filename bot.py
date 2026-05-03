app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("stats",     admin_stats))
    app.add_handler(CommandHandler("users",     admin_users))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("AutoReach Bot is running...")
    await app.updater.idle()
    await app.stop()
    await app.shutdown()


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in .env")

    init_db()

    import server
    server.start()
    logger.info("Keep-alive server started.")

    asyncio.run(run_bot())


if name == "main":
    main()
