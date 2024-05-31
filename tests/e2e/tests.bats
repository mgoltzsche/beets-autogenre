#!/usr/bin/env bats

assertGenre() {
	FMT='$genre_source | $genre | $genres'
	ACTUAL="$(beet ls $1 -f "$FMT")"
	[ "$ACTUAL" = "$2" ] || (
		echo "ERROR: Expected query '$1' with format '$FMT' to evaluate to '$2' but was '$ACTUAL'" >&2
		false
	)
}

tempConfigWithAutoEnabled() {
	TMP_CONF=/tmp/beets-autogenre-test-config.yaml
	cp -f /etc/beets/default-config.yaml $TMP_CONF
	printf '\nautogenre:\n  auto: true\n' >> $TMP_CONF
}

@test 'auto-detect song genre on import' {
	# Tuba Skinny - Jubilee Stomp
	tempConfigWithAutoEnabled
	beet -c $TMP_CONF ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=jft3BVoxqjo
	QUERY='Jubilee Stomp'
	assertGenre "$QUERY" 'lastfm | Jazz | Jazz, Blues'
}

@test 'auto-detect album genre on import' {
	# Miles Davis - Autumn Leaves
	tempConfigWithAutoEnabled
	beet -c $TMP_CONF ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=APKdKHIiNuE
	QUERY='Miles Davis Autumn Leaves Walkin'
	assertGenre "$QUERY" 'lastfm | Jazz | Jazz, Blues'
	QUERY='Autumn Leaves'
	[ "`beet ls -a "$QUERY"`" ] || (echo 'FAIL: No album imported!'; false)
	echo "ALBUM GENRE: `beet ls -a "$QUERY" -f '$genre'`"
	[ "`beet ls -a "$QUERY" -f '$genre'`" = 'Jazz' ] || (echo 'FAIL: Did not set album genre!'; false)
}

@test 'get genre from last.fm' {
	# Amadou & Mariam - Sénégal Fast Food
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=J43T8rEOg-I
	QUERY='title:Sénégal Fast Food'
	beet autogenre $QUERY
	assertGenre "$QUERY" 'lastfm | African | African'
}

@test 'force-overwrite genre' {
	# Amadou & Mariam - Sénégal Fast Food
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=J43T8rEOg-I
	QUERY='title:Sénégal Fast Food'
	beet modify -y $QUERY genre=fake-genre
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'lastfm | African | African'
}

@test 'get genre from last.fm track when remix/bootleg' {
	# Fugees - Ready Or Not (Champion Bootleg)
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=ts0WO6wJB3M
	QUERY='fugees ready or not champion bootleg'
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'lastfm | Drum And Bass | Drum And Bass, Electronic'
}

@test 'get genre from last.fm artist' {
	# Bellaire - Paris City Jazz
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=hyVVoLy4LSc
	QUERY='title:Paris City Jazz'
	beet autogenre $QUERY
	assertGenre "$QUERY" 'lastfm | Nu Jazz | Nu Jazz, House, Downtempo, Jazz, Electronic'
}

@test 'derive genre from track title' {
	# Rage Against the Machine - Wake Up (Rasticles drum n bass remix)
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=8tl7iOWZRa8
	QUERY='title:wake up (Rasticles drum n bass remix)'
	beet autogenre $QUERY
	assertGenre "$QUERY" 'title | Drum And Bass | Drum And Bass, Rock, Hip Hop, Electronic'
}

@test 'derive genre from album title' {
	# Reggae Jungle Drum and Bass Mix #9 New 2022
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=ZisHyhD0l_4
	QUERY='album:Reggae Jungle Drum and Bass Mix #9 New 2022 Rudy, a message to you'
	beet autogenre -fa $QUERY
	assertGenre "$QUERY" 'title | Ragga Drum And Bass | Ragga Drum And Bass, Drum And Bass, Electronic'
	echo ALBUM GENRE:
	beet ls -a 'Reggae Jungle Drum and Bass Mix #9 New 2022' -f '$genre'
	[ "`beet ls -a 'Reggae Jungle Drum and Bass Mix #9 New 2022' -f '$genre'`" = 'Ragga Drum And Bass' ] || (echo 'Should set album genre!'; false)
}

@test 'estimate genre using essentia' {
	# EttoreTechnoChannel - Hector Couto- Amanece
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=8CI2GjcCkuM
	QUERY='title:Hector Couto- Amanece'
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'essentia | Electronic | Electronic, Hip Hop, House'
}


@test 'specify genre manually' {
	ALBUM='Reggae Jungle Drum and Bass Mix #9 New 2022'
	beet autogenre -fa "album:$ALBUM"
	QUERY="album:$ALBUM Rudy, a message to you"
	beet autogenre --genre='Electronic' $QUERY
	assertGenre "$QUERY" 'user | Electronic | Electronic'
	# Should not touch genre of other items
	QUERY="album:$ALBUM Sizzla Livin"
	assertGenre "$QUERY" 'title | Ragga Drum And Bass | Ragga Drum And Bass, Dancehall, Reggae, Drum And Bass, Electronic'
}

@test 'preserve manually specified genre' {
	QUERY='album:Reggae Jungle Drum and Bass Mix #9 New 2022 Rudy, a message to you'
	beet autogenre -fa $QUERY
	assertGenre "$QUERY" 'user | Electronic | Electronic'
}

@test 'reset manually specified genre' {
	QUERY='album:Reggae Jungle Drum and Bass Mix #9 New 2022 Rudy, a message to you'
	beet autogenre --genre= $QUERY
	assertGenre "$QUERY" 'title | Ragga Drum And Bass | Ragga Drum And Bass, Drum And Bass, Electronic'
}
