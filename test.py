def test_valid(cldf_dataset, cldf_logger):
    assert cldf_dataset.validate(log=cldf_logger)


def test_forms(cldf_dataset):
    assert len(list(cldf_dataset["FormTable"])) == 2288
    assert any(f["Form"] == "ħamuxwusti" for f in cldf_dataset["FormTable"])


def test_parameters(cldf_dataset):
    assert len(list(cldf_dataset["ParameterTable"])) == 95


def test_languages(cldf_dataset):
    assert len(list(cldf_dataset["LanguageTable"])) == 25


def test_cognates(cldf_dataset):
    assert len(list(cldf_dataset["CognateTable"])) == 2074
    assert any(f["Form"] == "yɨlho" for f in cldf_dataset["CognateTable"])
