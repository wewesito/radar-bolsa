from radar.db.database import MIGRATIONS, Database
from radar.db.watchlist import WatchlistRepo


def test_add_list_remove(tmp_path):
    repo = WatchlistRepo(Database(tmp_path / "r.db"))
    assert repo.add("SAN.MC", "Banco Santander")
    assert repo.add("ITX.MC", "Inditex")
    assert not repo.add("SAN.MC", "Banco Santander")  # duplicado
    assert repo.tickers() == ["SAN.MC", "ITX.MC"]

    assert repo.remove("SAN.MC")
    assert not repo.remove("SAN.MC")
    assert repo.tickers() == ["ITX.MC"]


def test_persists_and_migrations_are_idempotent(tmp_path):
    path = tmp_path / "r.db"
    WatchlistRepo(Database(path)).add("SAN.MC", "Banco Santander")

    db = Database(path)  # reabrir no debe re-ejecutar migraciones ni perder datos
    assert WatchlistRepo(db).tickers() == ["SAN.MC"]
    with db.connect() as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
