from dataclasses import dataclass


@dataclass(frozen=True)
class Driver:
    """Represent a Formula 1 driver with identifying information."""

    last_name: str
    abbrev: str
    headshot_url: str
    year: int
    session: str
    team: str
    driver_color: str

    def __str__(self) -> str:
        """Return a string representation of the Driver.

        Returns:
            A string with the driver's last name and abbreviation.

        """
        return f"{self.last_name} ({self.abbrev}, {self.year}, {self.session}, {self.team}, {self.driver_color})"

    def __hash__(self) -> int:
        """Return a hash value for the Driver.

        Returns:
            An integer hash value based on the driver's immutable attributes.

        """
        return hash(
            (
                self.last_name,
                self.abbrev,
                self.headshot_url,
                self.year,
                self.session,
                self.team,
                self.driver_color,
            )
        )
