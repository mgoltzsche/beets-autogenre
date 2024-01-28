#!/usr/bin/env bats

assertGenre() {
	FMT='$genre_source | $genre_primary | $genre'
	ACTUAL="$(beet ls $1 -f "$FMT")"
	[ "$ACTUAL" = "$2" ] || (
		echo "ERROR: Expected query '$1' with format '$FMT' to evaluate to '$2' but was '$ACTUAL'" >&2
		false
	)
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
	assertGenre "$QUERY" 'lastfm | House | House, Downtempo, Jazz, Electronic'
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
}

@test 'estimate genre using essentia' {
	# EttoreTechnoChannel - Hector Couto- Amanece
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=8CI2GjcCkuM
	QUERY='title:Hector Couto- Amanece'
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'essentia | Electronic | Electronic, Hip Hop, House'
}


@test 'specify genre manually' {
	QUERY='album:Reggae Jungle Drum and Bass Mix #9 New 2022 Rudy, a message to you'
	beet autogenre --genre='Electronic' $QUERY
	assertGenre "$QUERY" 'user | Electronic | Electronic'
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
