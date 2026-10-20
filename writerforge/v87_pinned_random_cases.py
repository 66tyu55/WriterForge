"""V87 independent reader-only cold examination of two frozen raw passages.

Only metadata hashes, source SHA and SHA/offset proof, no private raw text.
These literal expectations came from the first REAL source audit output:
receipt 6565040f03811c51df6aa211b5f79305bb1a65fc8ebdfda5acc209259e515b9a.
"""
FIRST_AUDIT_RECEIPT_SHA256="6565040f03811c51df6aa211b5f79305bb1a65fc8ebdfda5acc209259e515b9a"
FROZEN_CASES=(
  {
    "genre_hint":"历史",
    "source_key_sha256":"7ade357517465167c6ea48fbaec2815f01c7e181603c3189157e9fb3adc6bbde",
    "source_sha256":"7dbc48ea45576b972dbf323ba77dea3e24b2394cc14650e23bc2c19788b77b97",
    "bytes":7029638,
    "fragment_start_char":772579,
    "fragment_end_char":774879,
    "fragment_sha256":"306239b74604419ccd06fbc6f4f5138d6cb59f919f8a886c44884d441e0062be",
    "fragment_unit_count":6,
    "first_read_visible_unit_sha256":[
       "71f5a2d7824ce9e5beb09c087f098515b1890c703cd940c71276fe1a2c9b6473",
       "b054107ecbe2478243cf45956f8748511580ba843d061de9837318f60841c0c7",
    ],
    "sealed_unread_unit_sha256":"b841fa9d52d0716dd956665fc4708d5d47ee65ec6bd1f96f732df313c3eb3682",
  },
  {
    "genre_hint":"科幻",
    "source_key_sha256":"bf474a0bc98f78f3787393a5ef74f5771447962b13c20f042d32a53a0bb17380",
    "source_sha256":"a41e5b86b2878bae3e1a42babd3a21714788ae36bbdc6c1faa1ccb11a0158172",
    "bytes":5306820,
    "fragment_start_char":2016726,
    "fragment_end_char":2019026,
    "fragment_sha256":"f19cce750e6b69c754740f38cdeaaaad56abc7865f840996f42d22188b28beda",
    "fragment_unit_count":6,
    "first_read_visible_unit_sha256":[
       "3602821bb53f0ab0d333ac276818268c61acdd6a3c1e09c9d6a0867ed1c39df9",
       "daeb096633538741448107a3329d7a7f7ebb13231c354ba0d6a0c87ac9b02d6c",
    ],
    "sealed_unread_unit_sha256":"3fd848b44aa76f202afa2604eba938764105ca5a171b2d372564fd81cdbf66de",
  },
)
