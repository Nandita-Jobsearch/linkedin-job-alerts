import scan


def test_other_language_roles_are_excluded():
    for title in ["Account Executive (German Speaker)",
                  "Sales Development Representative - Benelux",
                  "Business Development Representative, CEE",
                  "SDR - French, German, Dutch, Spanish or Italian",
                  "Account Manager L4 - DACH"]:
        assert scan._excluded(title), title


def test_english_and_irish_roles_are_kept():
    for title in ["Account Development Representative - English Speaking (SDR/BDR)",
                  "Business Development Representative, UKI",
                  "Graduate Marketing Executive",
                  "Sales Intern - Dublin"]:
        assert not scan._excluded(title), title
