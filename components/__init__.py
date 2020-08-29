#!/usr/bin/env python
"""The components module."""

from .picklablebase import PicklableBase
from .types import MessageType, UpdateType

from .instruments import (Instrument, WoodwindInstrument, BrassInstrument, HighBrassInstrument,
                          LowBrassInstrument, PercussionInstrument, Flute, Clarinet, Oboe, Bassoon,
                          Saxophone, SopranoSaxophone, AltoSaxophone, TenorSaxophone,
                          BaritoneSaxophone, Euphonium, Baritone, BaritoneHorn, Trombone, Tuba,
                          Trumpet, Flugelhorn, Horn, Drums, Guitar, BassGuitar, Conductor)
from .score import Score
from .userscore import UserScore
from .member import Member
from .gender import Gender
from .orchestra import Orchestra
from .question import Question
from .texts import question_text, PHOTO_OPTIONS
from .questioner import Questioner

__all__ = [
    # Instruments
    'Instrument',
    'WoodwindInstrument',
    'BrassInstrument',
    'HighBrassInstrument',
    'LowBrassInstrument',
    'PercussionInstrument',
    'Flute',
    'Clarinet',
    'Oboe',
    'Bassoon',
    'Saxophone',
    'SopranoSaxophone',
    'AltoSaxophone',
    'TenorSaxophone',
    'BaritoneSaxophone',
    'Euphonium',
    'Baritone',
    'Trombone',
    'Tuba',
    'Trumpet',
    'Flugelhorn',
    'Horn',
    'Drums',
    'BaritoneHorn',
    'Guitar',
    'BassGuitar',
    'Conductor',
    # AkaBlas related
    'Member',
    'Gender',
    'Orchestra',
    # Game related
    'UserScore',
    'Score',
    'Question',
    'Questioner',
    'question_text',
    'PHOTO_OPTIONS',
    # Utils related
    'PicklableBase',
    'MessageType',
    'UpdateType'
]
