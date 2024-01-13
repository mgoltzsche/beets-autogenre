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

@test 'derive genre from track title' {
	# Rage Against the Machine - Wake Up (Rasticles drum n bass remix)
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=8tl7iOWZRa8
	QUERY='title:wake up (Rasticles drum n bass remix)'
	beet autogenre $QUERY
	assertGenre "$QUERY" 'title | Drum And Bass | Drum And Bass, Rock, Hip Hop, Electronic'
}

@test 'force-overwrite genre' {
	QUERY='title:wake up (Rasticles drum n bass remix)'
	beet modify -y $QUERY genre=fake-genre
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'title | Drum And Bass | Drum And Bass, Rock, Hip Hop, Electronic'
}

@test 'estimate genre using essentia' {
	# EttoreTechnoChannel - Hector Couto- Amanece
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=8CI2GjcCkuM
	QUERY='title:Hector Couto- Amanece'
	beet autogenre -f $QUERY
	assertGenre "$QUERY" 'essentia | Electronic | Electronic, Hip Hop, House'
}

@test 'derive genre from album name' {
	# Reggae Jungle Drum and Bass Mix #9 New 2022
	beet ytimport -q --quiet-fallback=asis https://www.youtube.com/watch?v=ZisHyhD0l_4
	QUERY='album:Reggae Jungle Drum and Bass Mix #9 New 2022 Rudy, a message to you'
	beet autogenre -fa $QUERY
	assertGenre "$QUERY" 'title | Ragga Drum And Bass | Ragga Drum And Bass, Drum And Bass, Electronic'
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
