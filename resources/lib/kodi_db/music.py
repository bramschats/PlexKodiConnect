#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from logging import getLogger

from . import common
from .. import variables as v

LOG = getLogger('PLEX.kodi_db.music')


class KodiMusicDB(common.KodiDBBase):
    db_kind = 'music'

    def add_path(self, path):
        """
        Add the path (unicode) to the music DB, if it does not exist already.
        Returns the path id
        """
        # SQL won't return existing paths otherwise
        path = '' if path is None else path
        self.cursor.execute('SELECT idPath FROM path WHERE strPath = ?',
                            (path,))
        try:
            pathid = self.cursor.fetchone()[0]
        except TypeError:
            self.cursor.execute("SELECT COALESCE(MAX(idPath),0) FROM path")
            pathid = self.cursor.fetchone()[0] + 1
            self.cursor.execute('''
                                INSERT INTO path(idPath, strPath, strHash)
                                VALUES (?, ?, ?)
                                ''',
                                (pathid, path, '123'))
        return pathid

    def update_path(self, path, kodi_pathid):
        self.cursor.execute('''
            UPDATE path
            SET strPath = ?, strHash = ?
            WHERE idPath = ?
        ''', (path, '123', kodi_pathid))

    def song_id_from_filename(self, filename, path):
        """
        Returns the Kodi song_id from the Kodi music database or None if not
        found OR something went wrong.
        """
        self.cursor.execute('SELECT idPath FROM path WHERE strPath = ?',
                            (path, ))
        path_ids = self.cursor.fetchall()
        if len(path_ids) != 1:
            LOG.debug('Found wrong number of path ids: %s for path %s, abort',
                      path_ids, path)
            return
        self.cursor.execute('SELECT idSong FROM song WHERE strFileName = ? AND idPath = ?',
                            (filename, path_ids[0][0]))
        song_ids = self.cursor.fetchall()
        if len(song_ids) != 1:
            LOG.info('Found wrong number of songs %s, abort', song_ids)
            return
        return song_ids[0][0]

    def delete_song_from_song_artist(self, song_id):
        """
        Deletes son from song_artist table and possibly orphaned roles
        """
        self.cursor.execute('''
            SELECT idArtist, idRole FROM song_artist
            WHERE idSong = ? LIMIT 1
        ''', (song_id, ))
        artist = self.cursor.fetchone()
        if not artist:
            # No entry to begin with
            return
        # Delete the entry
        self.cursor.execute('DELETE FROM song_artist WHERE idSong = ?',
                            (song_id, ))

    def delete_album_from_discography(self, album_id):
        """
        Removes the album with id album_id from the table discography
        """
        # Need to get the album name as a string first!
        self.cursor.execute('SELECT strAlbum, iYear FROM album WHERE idAlbum = ? LIMIT 1',
                            (album_id, ))
        try:
            name, year = self.cursor.fetchone()
        except TypeError:
            return
        self.cursor.execute('SELECT idArtist FROM album_artist WHERE idAlbum = ? LIMIT 1',
                            (album_id, ))
        artist = self.cursor.fetchone()
        if not artist:
            return
        self.cursor.execute('DELETE FROM discography WHERE idArtist = ? AND strAlbum = ? AND strYear = ?',
                            (artist[0], name, year))

    def delete_song_from_song_genre(self, song_id):
        """
        Deletes the one entry with id song_id from the song_genre table.
        Will also delete orphaned genres from genre table
        """
        self.cursor.execute('SELECT idGenre FROM song_genre WHERE idSong = ?',
                            (song_id, ))
        genres = self.cursor.fetchall()
        self.cursor.execute('DELETE FROM song_genre WHERE idSong = ?',
                            (song_id, ))
        # Check for orphaned genres in both song_genre and album_genre tables
        for genre in genres:
            self.cursor.execute('SELECT idGenre FROM song_genre WHERE idGenre = ? LIMIT 1',
                                (genre[0], ))
            if not self.cursor.fetchone():
                self.cursor.execute('SELECT idGenre FROM album_genre WHERE idGenre = ? LIMIT 1',
                                    (genre[0], ))
                if not self.cursor.fetchone():
                    self.cursor.execute('DELETE FROM genre WHERE idGenre = ?',
                                        (genre[0], ))

    def delete_album_from_album_genre(self, album_id):
        """
        Deletes the one entry with id album_id from the album_genre table.
        Will also delete orphaned genres from genre table
        """
        self.cursor.execute('SELECT idGenre FROM album_genre WHERE idAlbum = ?',
                            (album_id, ))
        genres = self.cursor.fetchall()
        self.cursor.execute('DELETE FROM album_genre WHERE idAlbum = ?',
                            (album_id, ))
        # Check for orphaned genres in both album_genre and song_genre tables
        for genre in genres:
            self.cursor.execute('SELECT idGenre FROM album_genre WHERE idGenre = ? LIMIT 1',
                                (genre[0], ))
            if not self.cursor.fetchone():
                self.cursor.execute('SELECT idGenre FROM song_genre WHERE idGenre = ? LIMIT 1',
                                    (genre[0], ))
                if not self.cursor.fetchone():
                    self.cursor.execute('DELETE FROM genre WHERE idGenre = ?',
                                        (genre[0], ))

    def new_album_id(self):
        self.cursor.execute('SELECT COALESCE(MAX(idAlbum), 0) FROM album')
        return self.cursor.fetchone()[0] + 1

    def add_album_17(self, *args):
        """
        strReleaseType: 'album' or 'single'
        """
        self.cursor.execute('''
            INSERT INTO album(
                idAlbum,
                strAlbum,
                strMusicBrainzAlbumID,
                strArtists,
                strGenres,
                iYear,
                bCompilation,
                strReview,
                strImage,
                strLabel,
                iUserrating,
                lastScraped,
                strReleaseType)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (args))

    def update_album_17(self, *args):
        self.cursor.execute('''
            UPDATE album
            SET strAlbum = ?,
                strMusicBrainzAlbumID = ?,
                strArtists = ?,
                strGenres = ?,
                iYear = ?,
                bCompilation = ?,
                strReview = ?,
                strImage = ?,
                strLabel = ?,
                iUserrating = ?,
                lastScraped = ?,
                strReleaseType = ?
            WHERE idAlbum = ?
        ''', (args))

    def add_album(self, *args):
        """
        strReleaseType: 'album' or 'single'
        """
        self.cursor.execute('''
            INSERT INTO album(
                idAlbum,
                strAlbum,
                strMusicBrainzAlbumID,
                strArtistDisp,
                strGenres,
                iYear,
                bCompilation,
                strReview,
                strImage,
                strLabel,
                iUserrating,
                lastScraped,
                strReleaseType)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (args))

    def update_album(self, *args):
        self.cursor.execute('''
            UPDATE album
            SET strAlbum = ?,
                strMusicBrainzAlbumID = ?,
                strArtistDisp = ?,
                strGenres = ?,
                iYear = ?,
                bCompilation = ?,
                strReview = ?,
                strImage = ?,
                strLabel = ?,
                iUserrating = ?,
                lastScraped = ?,
                strReleaseType = ?,
            WHERE idAlbum = ?
        ''', (args))

    def add_albumartist(self, artist_id, kodi_id, artistname):
        self.cursor.execute('''
            INSERT OR REPLACE INTO album_artist(
                idArtist,
                idAlbum,
                strArtist)
            VALUES (?, ?, ?)
        ''', (artist_id, kodi_id, artistname))

    def add_discography(self, artist_id, albumname, year):
        self.cursor.execute('''
            INSERT OR REPLACE INTO discography(
                idArtist,
                strAlbum,
                strYear)
            VALUES (?, ?, ?)
        ''', (artist_id, albumname, year))

    def add_music_genres(self, kodiid, genres, mediatype):
        """
        Adds a list of genres (list of unicode) for a certain Kodi item
        """
        if mediatype == "album":
            # Delete current genres for clean slate
            self.cursor.execute('DELETE FROM album_genre WHERE idAlbum = ?',
                                (kodiid, ))
            for genre in genres:
                self.cursor.execute('SELECT idGenre FROM genre WHERE strGenre = ?',
                                    (genre, ))
                try:
                    genreid = self.cursor.fetchone()[0]
                except TypeError:
                    # Create the genre
                    self.cursor.execute('SELECT COALESCE(MAX(idGenre),0) FROM genre')
                    genreid = self.cursor.fetchone()[0] + 1
                    self.cursor.execute('INSERT INTO genre(idGenre, strGenre) VALUES(?, ?)',
                                        (genreid, genre))
                self.cursor.execute('''
                    INSERT OR REPLACE INTO album_genre(
                        idGenre,
                        idAlbum)
                    VALUES (?, ?)
                ''', (genreid, kodiid))
        elif mediatype == "song":
            # Delete current genres for clean slate
            self.cursor.execute('DELETE FROM song_genre WHERE idSong = ?',
                                (kodiid, ))
            for genre in genres:
                self.cursor.execute('SELECT idGenre FROM genre WHERE strGenre = ?',
                                    (genre, ))
                try:
                    genreid = self.cursor.fetchone()[0]
                except TypeError:
                    # Create the genre
                    self.cursor.execute('SELECT COALESCE(MAX(idGenre),0) FROM genre')
                    genreid = self.cursor.fetchone()[0] + 1
                    self.cursor.execute('INSERT INTO genre(idGenre, strGenre) values(?, ?)',
                                        (genreid, genre))
                self.cursor.execute('''
                    INSERT OR REPLACE INTO song_genre(
                        idGenre,
                        idSong,
                        iOrder)
                    VALUES (?, ?, ?)
                ''', (genreid, kodiid, 0))

    def add_song_id(self):
        self.cursor.execute('SELECT COALESCE(MAX(idSong),0) FROM song')
        return self.cursor.fetchone()[0] + 1

    def add_song(self, *args):
        self.cursor.execute('''
            INSERT INTO song(
                idSong,
                idAlbum,
                idPath,
                strArtistDisp,
                strGenres,
                strTitle,
                iTrack,
                iDuration,
                iYear,
                strFileName,
                strMusicBrainzTrackID,
                iTimesPlayed,
                lastplayed,
                rating,
                iStartOffset,
                iEndOffset,
                mood,
                dateAdded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (args))

    def add_song_17(self, *args):
        self.cursor.execute('''
            INSERT INTO song(
                idSong,
                idAlbum,
                idPath,
                strArtists,
                strGenres,
                strTitle,
                iTrack,
                iDuration,
                iYear,
                strFileName,
                strMusicBrainzTrackID,
                iTimesPlayed,
                lastplayed,
                rating,
                iStartOffset,
                iEndOffset,
                mood,
                dateAdded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (args))

    def update_song(self, *args):
        self.cursor.execute('''
            UPDATE song
            SET idAlbum = ?,
                strArtistDisp = ?,
                strGenres = ?,
                strTitle = ?,
                iTrack = ?,
                iDuration = ?,
                iYear = ?,
                strFilename = ?,
                iTimesPlayed = ?,
                lastplayed = ?,
                rating = ?,
                comment = ?,
                mood = ?,
                dateAdded = ?
            WHERE idSong = ?
        ''', (args))

    def update_song_17(self, *args):
        self.cursor.execute('''
            UPDATE song
            SET idAlbum = ?,
                strArtists = ?,
                strGenres = ?,
                strTitle = ?,
                iTrack = ?,
                iDuration = ?,
                iYear = ?,
                strFilename = ?,
                iTimesPlayed = ?,
                lastplayed = ?,
                rating = ?,
                comment = ?,
                mood = ?,
                dateAdded = ?
            WHERE idSong = ?
        ''', (args))

    def path_id_from_song(self, kodi_id):
        self.cursor.execute('SELECT idPath FROM song WHERE idSong = ? LIMIT 1',
                            (kodi_id, ))
        try:
            return self.cursor.fetchone()[0]
        except TypeError:
            pass

    def add_artist(self, name, musicbrainz):
        """
        Adds a single artist's name to the db
        """
        self.cursor.execute('''
            SELECT idArtist, strArtist
            FROM artist
            WHERE strMusicBrainzArtistID = ?
        ''', (musicbrainz, ))
        try:
            result = self.cursor.fetchone()
            artistid = result[0]
            artistname = result[1]
        except TypeError:
            self.cursor.execute('SELECT idArtist FROM artist WHERE strArtist = ? COLLATE NOCASE',
                                (name, ))
            try:
                artistid = self.cursor.fetchone()[0]
            except TypeError:
                # Krypton has a dummy first entry idArtist: 1  strArtist:
                # [Missing Tag] strMusicBrainzArtistID: Artist Tag Missing
                self.cursor.execute('SELECT COALESCE(MAX(idArtist),1) FROM artist')
                artistid = self.cursor.fetchone()[0] + 1
                self.cursor.execute('''
                    INSERT INTO artist(
                        idArtist,
                        strArtist,
                        strMusicBrainzArtistID)
                    VALUES (?, ?, ?)
                ''', (artistid, name, musicbrainz))
        else:
            if artistname != name:
                self.cursor.execute('UPDATE artist SET strArtist = ? WHERE idArtist = ?',
                                    (name, artistid,))
        return artistid

    def update_artist(self, *args):
        self.cursor.execute('''
            UPDATE artist
            SET strGenres = ?,
                strBiography = ?,
                strImage = ?,
                strFanart = ?,
                lastScraped = ?
            WHERE idArtist = ?
        ''', (args))

    def remove_song(self, kodi_id):
        self.cursor.execute('DELETE FROM song WHERE idSong = ?', (kodi_id, ))

    def remove_path(self, path_id):
        self.cursor.execute('DELETE FROM path WHERE idPath = ?', (path_id, ))

    def add_song_artist(self, artist_id, song_id, artist_name):
        self.cursor.execute('''
            INSERT OR REPLACE INTO song_artist(
                idArtist,
                idSong,
                idRole,
                iOrder,
                strArtist)
            VALUES (?, ?, ?, ?, ?)
        ''', (artist_id, song_id, 1, 0, artist_name))

    def add_albuminfosong(self, song_id, album_id, track_no, track_title,
                          runtime):
        """
        Kodi 17 only
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO albuminfosong(
                idAlbumInfoSong,
                idAlbumInfo,
                iTrack,
                strTitle,
                iDuration)
            VALUES (?, ?, ?, ?, ?)
        ''', (song_id, album_id, track_no, track_title, runtime))

    def update_userrating(self, kodi_id, kodi_type, userrating):
        """
        Updates userrating for songs and albums
        """
        if kodi_type == v.KODI_TYPE_SONG:
            column = 'userrating'
            identifier = 'idSong'
        elif kodi_type == v.KODI_TYPE_ALBUM:
            column = 'iUserrating'
            identifier = 'idAlbum'
        self.cursor.execute('''UPDATE %s SET %s = ? WHERE ? = ?'''
                            % (kodi_type, column),
                            (userrating, identifier, kodi_id))

    def remove_albuminfosong(self, kodi_id):
        """
        Kodi 17 only
        """
        self.cursor.execute('DELETE FROM albuminfosong WHERE idAlbumInfoSong = ?',
                            (kodi_id, ))

    def remove_album(self, kodi_id):
        if v.KODIVERSION < 18:
            self.cursor.execute('DELETE FROM albuminfosong WHERE idAlbumInfo = ?',
                                (kodi_id, ))
        self.cursor.execute('DELETE FROM album_artist WHERE idAlbum = ?',
                            (kodi_id, ))
        self.cursor.execute('DELETE FROM album WHERE idAlbum = ?', (kodi_id, ))

    def remove_artist(self, kodi_id):
        self.cursor.execute('DELETE FROM album_artist WHERE idArtist = ?',
                            (kodi_id, ))
        self.cursor.execute('DELETE FROM artist WHERE idArtist = ?',
                            (kodi_id, ))
        self.cursor.execute('DELETE FROM song_artist WHERE idArtist = ?',
                            (kodi_id, ))
        self.cursor.execute('DELETE FROM discography WHERE idArtist = ?',
                            (kodi_id, ))
