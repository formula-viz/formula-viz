"""Generate necessary metadata for creating a YouTube video."""

from src.models.config import Config


class YoutubeText:
    """Get contents of text fields in a YouTube video."""

    @staticmethod
    def get_title(config: Config):
        """Get the title of the YouTube video."""
        youtube = config["socials"]["youtube"]
        assert youtube is not None
        if youtube["title"]:
            return youtube["title"]

        if config["mixed_mode"]["enabled"]:
            return f"{config['mixed_mode']['title']} #f1"
        if config["type"] == "rest-of-field":
            return f"How {config['drivers'][0]} won P1 at {config['track'].title()} Qualifying {config['year']} Simulation #f1"
        else:
            # there could be several drivers here
            # say Norris, Verstappen, Russel, we want:
            # Norris vs Verstappen vs Russell
            drivers = config["drivers"]
            drivers_str = " and ".join(drivers[1:])

            return f"How {drivers[0]} beat {drivers_str} at {config['track'].title()} Qualifying {config['year']} Simulation #f1"

    @staticmethod
    def get_description(config: Config):
        """Get the description of the YouTube video."""
        description = """
        Uploading every qualifying session of the F1 season.

        Join the discord to give feedback and make video requests.
        """
        description = "Uploading videos every qualifying session of the formula 1 in addition to historical recaps leading up to the race weekend."
        description += "\n\nJoin the discord community: https://discord.gg/ZMBTwhjScp"
        description += "\n\nGenerated using telemetry car data provided by Formula1 via the FastF1 api."
        description += "\n\n(not affiliated with Formula 1 or any of its subsidiaries)"

        return description


def main(config: Config):
    """Generate necessary metadata for creating a YouTube video."""
    yt_config = config["socials"]["youtube"]
    if yt_config is None:
        raise ValueError("Youtube config not found")

    body = {
        "snippet": {
            "title": YoutubeText.get_title(config),
            "description": YoutubeText.get_description(config),
            # "tags": yt_config.video_tags,
            # "categoryId": yt_config.video_category_id,
        },
        "status": {
            "privacyStatus": yt_config["visibility"],
            "selfDeclaredMadeForKids": False,
        },
    }

    if "publish_at" in yt_config and yt_config["publish_at"]:
        body["status"]["publishAt"] = yt_config["publish_at"]

    return body
