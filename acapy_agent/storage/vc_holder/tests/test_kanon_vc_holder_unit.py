import pytest


class _Sess:
    def __init__(self, holder):
        self.holder = holder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Profile:
    def __init__(self):
        self.records = {}

    def session(self):
        return _Sess(self)


@pytest.fixture
def patched_vc(monkeypatch):
    from acapy_agent.storage.vc_holder import kanon as module

    class _KanonStorage:
        def __init__(self, sess):
            self._db = sess.holder

        async def add_record(self, rec):
            if (rec.type, rec.id) in self._db.records:
                raise Exception("dup")
            self._db.records[(rec.type, rec.id)] = rec

        async def get_record(self, typ, rec_id):
            rec = self._db.records.get((typ, rec_id))
            if not rec:
                raise Exception("nf")
            return rec

        async def find_record(self, typ, tagf):
            for (t, _), rec in self._db.records.items():
                if t == typ and rec.tags.get("given_id") == tagf.get("given_id"):
                    return rec
            raise Exception("nf")

        async def delete_record(self, rec):
            self._db.records.pop((rec.type, rec.id), None)

    class _Search:
        def __init__(self, prof):
            self.prof = prof

        def search_records(self, typ, query):
            class _S:
                async def close(self):
                    return None

                async def fetch(self, max_count=None):
                    return list(self.prof.records.values())

            s = _S()
            s.prof = self.prof
            return s

    monkeypatch.setattr(module, "KanonStorage", _KanonStorage)
    monkeypatch.setattr(module, "KanonStorageSearch", _Search)
    return module


@pytest.mark.asyncio
async def test_store_retrieve_delete_and_search(patched_vc):
    module = patched_vc
    prof = _Profile()
    holder = module.KanonVCHolder(prof)
    from acapy_agent.storage.vc_holder.vc_record import VCRecord

    rec = VCRecord(
        contexts={"c"},
        expanded_types={"t"},
        schema_ids={"s"},
        issuer_id="iss",
        subject_ids={"sub"},
        proof_types={"pt"},
        cred_value={"x": 1},
        given_id="gid",
        cred_tags={"k": "v"},
        record_id="rid1",
    )
    await holder.store_credential(rec)
    got = await holder.retrieve_credential_by_id("rid1")
    assert got.record_id == "rid1"
    got2 = await holder.retrieve_credential_by_given_id("gid")
    assert got2.given_id == "gid"

    srch = holder.search_credentials(
        types=["t"],
        schema_ids=["s"],
        issuer_id="iss",
        given_id="gid",
        tag_query={"z": 1},
        pd_uri_list=["u"],
    )
    recs = await srch.fetch()
    assert recs and recs[0].record_id == "rid1"
    await srch.close()

    await holder.delete_credential(rec)
