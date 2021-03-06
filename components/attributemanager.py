#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""This module contains the classes for attributes."""
from __future__ import annotations

import random
import datetime as dtm
from collections import defaultdict
from copy import deepcopy
from threading import Lock
from typing import (
    Callable,
    Any,
    List,
    TypeVar,
    Dict,
    Set,
    Optional,
    Tuple,
    FrozenSet,
    Generic,
    TYPE_CHECKING,
    Union,
    cast,
    overload,
    Literal,
    Iterable,
)

from components import PicklableBase, Gender

if TYPE_CHECKING:
    from components import Member

AttributeType = TypeVar('AttributeType')
MemberDict = Dict[AttributeType, Set['Member']]


class AttributeManager(PicklableBase, Generic[AttributeType]):
    """
    A class to keep track on a specific attribute of :class:`components.Member` instances and
    what questions can be asked based on it.

    Note:
        Instances of this class are comparable by means of equality by :attr:`description`. They
        are also comparable to strings by the same definition.

    Note:
        If :meth:get_members_attribute returns a list, it will *not* be treated as a single value
        but instead as the member having multiple values for this attribute.

    Attributes:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
        gendered_questions: Whether questions with tis attribute as hint should try to
            list only members with the same gender as the hint member.

    Args:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
        get_members_attribute: A callable that extracts the attribute managed by this class from
            a :class:`components.Member` instance. Defaults to

            .. code:: python

                lambda member: member[self.description]
        gendered_questions: Optional. Whether questions with tis attribute as hint should try to
            list only members with the same gender as the hint member. Defaults to :obj:`False`.
    """

    def __init__(
        self,
        description: str,
        questionable_attributes: List[Union[AttributeManager, str]],
        get_members_attribute: Callable[
            ['Member'], Optional[Union[AttributeType, List[AttributeType]]]
        ] = None,
        gendered_questions: bool = False,
    ) -> None:
        self.description = description
        self.questionable_attributes = questionable_attributes
        self.gendered_questions = gendered_questions
        self._data: MemberDict = defaultdict(set)
        self._lock = Lock()

        if not get_members_attribute:
            self._get_members_attribute = self._default_gma
        else:
            self._get_members_attribute = get_members_attribute  # type: ignore

    @property
    def data(self) -> MemberDict:  # pylint: disable=C0116
        return self._data

    def _default_gma(
        self, member: 'Member'
    ) -> Optional[Union[AttributeType, List[AttributeType]]]:
        return member[self.description]  # type: ignore

    def get_members_attribute(
        self, member: 'Member'
    ) -> Optional[Union[AttributeType, List[AttributeType]]]:
        """
        Gives the attribute of :attr:`member` that is managed by this instance.

        Args:
            member: The member.
        """
        return self._get_members_attribute(member)

    def _gma_as_list(self, member: Member) -> Optional[List[AttributeType]]:
        attr = self.get_members_attribute(member)
        if isinstance(attr, list):
            return attr
        if attr is None:
            return None
        return [attr]

    def members_share_attribute(self, member1: Member, member2: Member) -> bool:
        """
        Checks if :attr:`member1` and :attr:`member2` share the attribute described by this
        instance. This usually means a check by equality except in the case, where the attribute
        is given by a list. In this case, :obj:`True` is returned, if the lists have at least one
        common element.

        Args:
            member1: Member 1.
            member2: Member 2.
        """
        attrs1 = self._gma_as_list(member1)
        attrs2 = self._gma_as_list(member2)
        if attrs1 and attrs2:
            return bool(set(attrs1).intersection(attrs2))
        return False

    def register_member(self, member: 'Member') -> None:
        """
        Registers a new member.

        Note:
            Copies the member so changes to the instance wont directly affect the orchestra.
            Use :meth:`update_member` to update the information about this member.

        Args:
            member: The new member
        """
        if member in self.available_members:
            raise RuntimeError('Member is already registered.')

        new_member = deepcopy(member)
        attributes = self._gma_as_list(new_member)
        if not attributes:
            return
        with self._lock:
            for attr in attributes:
                self.data[attr].add(new_member)

    def kick_member(self, member: 'Member') -> None:
        """
        Kicks a member, if present.

        Args:
            member: The member to kick.
        """
        with self._lock:
            for attr in list(self.data.keys()):
                self.data[attr].discard(member)
                # Make sure emtpy sets are deleted
                if len(self.data[attr]) == 0:
                    self.data.pop(attr)

    def update_member(self, member: 'Member') -> None:
        """
        Updates the information of a member.

        Note:
            As :meth:`register_user`, this will copy the
            member. To update the information again, call this method again.

        Args:
            member: The member with new information.
        """
        self.kick_member(member)
        self.register_member(member)

    def _distinct_values_for_member(
        self, data: MemberDict, attribute_manager: AttributeManager, member: Member
    ) -> Set[AttributeType]:
        members_attributes = self._gma_as_list(member)
        if members_attributes is None:
            return set()

        def test_condition(key: AttributeType) -> bool:
            return not any(
                attribute_manager.members_share_attribute(member, m)
                or self.members_share_attribute(member, m)
                for m in data[key]
            )

        with self._lock:
            return set(
                key for key in data if key not in members_attributes and test_condition(key)
            )

    def distinct_values_for_member(
        self, attribute_manager: AttributeManager, member: Member
    ) -> Set[AttributeType]:
        """
        Given an attribute manager and a member from it's available members, this returns a set
        of the distinct attribute values appearing across the members ``m`` in
        :attr:`available_members` who satisfy:

        1. ``not self.members_share_attribute(member, m)``
        2. ``not attribute_manager.members_share_attribute(member, m)``

        If ``self.get_members_attribute(member)`` is :obj:`None`, will just return an empty set.

        Args:
            attribute_manager: The manager describing the attribute serving as hint.
            member: The member.
        """
        return self._distinct_values_for_member(self.data, attribute_manager, member)

    def unique_attributes_of(self, member: Member) -> List[AttributeType]:
        """
        Given a member this returns a list of attribute values managed by this instance that only
        appear for that member, making it the unique correct answer for it.

        Note:
            This method is called *only* for requests for free text questions. Therefore subclasses
            may decide to return something different from :meth:`get_members_attribute`.

        Args:
            member: The member.
        """
        attributes = self._gma_as_list(member)
        if attributes is None:
            return []
        with self._lock:
            return [attr for attr in attributes if len(self.data[attr].difference({member})) == 0]

    @property
    def available_members(self) -> FrozenSet['Member']:
        """
        All the members that have the attribute managed by this instance.
        """
        with self._lock:
            return frozenset(set().union(*self.data.values()))  # type: ignore

    def is_hintable_with_member(
        self, attribute_manager: AttributeManager, member: Member, multiple_choice: bool = True
    ) -> bool:
        """
        If the given members attribute managed by this instance can be used as hint where the
        question is the attribute managed by :attr:`attribute_manager`.

        Args:
            attribute_manager: The manager describing the attribute serving as question.
            member: The member.
            multiple_choice: Whether this is a multiple choice question or not. Defaults to
                :obj:`True`
        """
        if multiple_choice:
            return len(attribute_manager.distinct_values_for_member(self, member)) >= 3
        return (
            member in attribute_manager.available_members
            and len(self.unique_attributes_of(member)) >= 1
        )

    def is_hintable_with(
        self,
        attribute_manager: AttributeManager,
        multiple_choice: bool = True,
        exclude_members: Iterable[Member] = None,
    ) -> bool:
        """
        If the attribute managed by this instance can be used as hint where the question is the
        attribute managed by :attr:`attribute_manager`.

        Args:
            attribute_manager: The manager describing the attribute serving as question.
            multiple_choice: Whether this is a multiple choice question or not. Defaults to
                :obj:`True`
            exclude_members: Optional. Members to exclude from serving as hint.
        """
        if attribute_manager not in self.questionable_attributes:
            return False
        if self.available_members.isdisjoint(attribute_manager.available_members):
            return False
        return any(
            self.is_hintable_with_member(attribute_manager, m, multiple_choice=multiple_choice)
            for m in self.available_members.intersection(
                attribute_manager.available_members
            ).difference(exclude_members or [])
        )

    def draw_hint_member(
        self,
        attribute_manager: AttributeManager,
        multiple_choice: bool = True,
        exclude_members: Iterable[Member] = None,
    ) -> 'Member':
        """
        Draws a member to build a question for.

        Args:
            attribute_manager: The manager describing the attribute serving as question.
            multiple_choice: Whether this is a multiple choice question or not. Defaults to
                :obj:`True`
            exclude_members: Optional. Members to exclude from serving as hint.

        Raises:
            ValueError: If :attr:`attribute_manager` is not a valid question for this instance in
                general
            ValueError: If :attr:`attribute_manager` is currently not questionable for this
                instance
        """
        if attribute_manager not in self.questionable_attributes:
            raise ValueError(
                f'{attribute_manager.description} is not a valid question for {self.description}'
            )
        if not self.is_hintable_with(
            attribute_manager, multiple_choice=multiple_choice, exclude_members=exclude_members
        ):
            raise RuntimeError(
                f'{self.description} currently not hintable for '
                f'{attribute_manager.description}'
            )

        potential_hint_members = list(
            m
            for m in self.available_members.intersection(
                attribute_manager.available_members
            ).difference(exclude_members or [])
            if self.is_hintable_with_member(attribute_manager, m, multiple_choice=multiple_choice)
        )
        return random.choice(potential_hint_members)

    def draw_question_attributes(
        self, attribute_manager: AttributeManager, member: 'Member'
    ) -> Tuple[Tuple[AttributeType, AttributeType, AttributeType, AttributeType], int]:
        """
        Draws question attributes for the given member. The first output is a 4-tuple of the
        drawn options. The second output is the index of the correct answer, i.e. the attribute
        of :attr:`member`.

        Args:
            attribute_manager: The manager describing the attribute serving as hint.
            member: The member that defines the correct answer.
        """
        correct_attributes = self._gma_as_list(member)

        if not correct_attributes:
            raise RuntimeError(f'Given member has no attribute {self.description}')
        correct_attribute = random.choice(correct_attributes)

        dvs = list(self.distinct_values_for_member(attribute_manager, member))

        if len(dvs) < 3:
            raise RuntimeError(
                f'Given member {member} is not hintable for attribute {self.description}!'
            )

        attributes = random.sample(dvs, 3)
        attributes.append(correct_attribute)

        random.shuffle(attributes)

        return tuple(attributes), attributes.index(correct_attribute)  # type: ignore

    @overload
    def build_question_with(
        self,
        attribute_manager: AttributeManager,
        multiple_choice: Literal[False],
        exclude_members: Iterable[Member] = None,
    ) -> Tuple[Member, AttributeType, Union[Any, List[Any]]]:
        ...

    @overload
    def build_question_with(  # noqa: F811
        self,
        attribute_manager: AttributeManager,
        multiple_choice: Literal[True],
        exclude_members: Iterable[Member] = None,
    ) -> Tuple[Member, AttributeType, Tuple[Any, Any, Any, Any], int]:
        ...

    def build_question_with(  # noqa: F811
        self,
        attribute_manager: AttributeManager,
        multiple_choice: bool = True,
        exclude_members: Iterable[Member] = None,
    ) -> Union[
        Tuple[Member, AttributeType, Tuple[Any, Any, Any, Any], int],
        Tuple[Member, AttributeType, Any],
    ]:
        """
        Builds a question where this instance is serving as hint and :attr:`attribute_manager`
        servers as question. For multiple choice questions the output is a 4-tuple of

        1. The member serving as hint
        2. The attribute to be given as hint
        3. The attributes to be given as options for the answer
        4. The index of the correct answer.

        For free text questions, the output is a 3-tuple of

        1. The member serving as hint
        2. The attribute to be given as hint
        3. The correct answer/a list of correct answers.

        Args:
            attribute_manager: The manager describing the attribute serving as question.
            multiple_choice: Whether this is a multiple choice question or not. Defaults to
                :obj:`True`
            exclude_members: Optional. Members to exclude from serving as hint. Only relevant, if
             ``multiple_choice is True``

        Raises:
            ValueError: If :attr:`attribute_manager` is not a valid question for this instance in
                general
            ValueError: If :attr:`attribute_manager` is currently not questionable for this
                instance
        """
        hint_member = self.draw_hint_member(
            attribute_manager, multiple_choice=multiple_choice, exclude_members=exclude_members
        )

        if multiple_choice:
            # draw_hint_member makes sure that this is not None, but MyPy can't see that ...
            hint_attributes = cast(list, self._gma_as_list(hint_member))
            attributes, idx = attribute_manager.draw_question_attributes(self, hint_member)
            return hint_member, random.choice(hint_attributes), attributes, idx

        hint_attributes = self.unique_attributes_of(hint_member)
        attribute = attribute_manager.get_members_attribute(hint_member)

        return hint_member, random.choice(hint_attributes), attribute

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AttributeManager):
            return self.description == other.description
        if isinstance(other, str):
            return self.description == other
        return False

    def __repr__(self) -> str:
        return f'AttributeManager({self.description})'


class NameManager(AttributeManager):
    """
    Subclass of :class:`AttributeManager` for first and full names. This is needed, as the gender
    of a member needs to be taken into account.

    Attributes:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.

    Args:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
        get_members_attribute: A callable that extracts the attribute managed by this class from
            a :class:`components.Member` instance. Defaults to

            .. code:: python

                lambda member: member[self.description]
    """

    def __init__(
        self,
        description: str,
        questionable_attributes: List[Union[AttributeManager, str]],
        get_members_attribute: Callable[
            ['Member'], Optional[Union[AttributeType, List[AttributeType]]]
        ] = None,
    ) -> None:
        super().__init__(
            description=description,
            questionable_attributes=questionable_attributes,
            get_members_attribute=get_members_attribute,
            gendered_questions=True,
        )
        self.male_data: MemberDict = defaultdict(set)
        self.female_data: MemberDict = defaultdict(set)

    def register_member(self, member: 'Member') -> None:
        """
        Registers a new member.

        Note:
            Copies the member so changes to the instance wont directly affect the orchestra.
            Use :meth:`update_member` to update the information about this member.

        Args:
            member: The new member
        """
        super().register_member(member)

        new_member = deepcopy(member)
        attribute = self.get_members_attribute(new_member)
        if attribute and member.gender:
            with self._lock:
                if new_member.gender == Gender.MALE:
                    self.male_data[attribute].add(new_member)
                else:
                    self.female_data[attribute].add(new_member)

    def kick_member(self, member: 'Member') -> None:
        """
        Kicks a member, if present.

        Args:
            member: The member to kick.
        """
        super().kick_member(member)
        with self._lock:
            for data in [self.female_data, self.male_data]:
                for attr in list(data.keys()):
                    data[attr].discard(member)
                    # Make sure emtpy sets are deleted
                    if len(data[attr]) == 0:
                        data.pop(attr)

    def distinct_values_for_member(
        self, attribute_manager: AttributeManager, member: Member
    ) -> Set[AttributeType]:
        """
        If the member has a gender, this acts just like
        :meth:`AttributeManager.distinct_values_for_member`. If it does not, an empty set is
        returned.

        Args:
            attribute_manager: The manager describing the attribute serving as hint.
            member: The member.
        """
        if attribute_manager.gendered_questions:
            members_attribute = self.get_members_attribute(member)
            if members_attribute is None or (member.first_name and member.gender is None):
                return set()

            if member.gender:
                data = self.male_data if member.gender == Gender.MALE else self.female_data
                return self._distinct_values_for_member(data, attribute_manager, member)

            return super().distinct_values_for_member(attribute_manager, member)

        return super().distinct_values_for_member(attribute_manager, member)


class PhotoManager(NameManager):
    """
    Subclass of :class:`AttributeManager` for photo file IDs. This is needed, as the gender
    of a member needs to be taken into account.

    Attributes:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.

    Args:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
    """

    def __init__(
        self, description: str, questionable_attributes: List[Union[AttributeManager, str]]
    ) -> None:
        super().__init__(
            description=description,
            questionable_attributes=questionable_attributes,
            get_members_attribute=self.get_members_attribute,
        )
        self.male_data: MemberDict = defaultdict(set)
        self.female_data: MemberDict = defaultdict(set)

    @staticmethod
    def get_members_attribute(member: 'Member') -> Optional[str]:
        return member.photo_file_id

    def distinct_values_for_member(
        self, attribute_manager: AttributeManager, member: Member
    ) -> Set[AttributeType]:
        """
        If the member has a gender, this acts just like
        :meth:`AttributeManager.distinct_values_for_member`. If it does not, an empty set is
        returned.

        Args:
            attribute_manager: The manager describing the attribute serving as hint.
            member: The member.
        """
        if attribute_manager.gendered_questions:
            members_attribute = self.get_members_attribute(member)
            if members_attribute is None or member.gender is None:
                return set()

            data = self.male_data if member.gender == Gender.MALE else self.female_data
            return self._distinct_values_for_member(data, attribute_manager, member)

        return super().distinct_values_for_member(attribute_manager, member)


class ChangingAttributeManager(AttributeManager):
    """
    Subclass of :class:`AttributeManager` that updates it's members attributes once a day. This is
    needed, for attributes like age, which can change on a daily basis.

    Attributes:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
        gendered_questions: Whether questions with tis attribute as hint should try to
            list only members with the same gender as the hint member.

    Args:
        description: A description of the attribute the instance manages.
        questionable_attributes: A list of :class:`components.AttributeManager` instances that
            manages attributes, which are available as questions for the attribute this instance
            manages.
        get_members_attribute: A callable that extracts the attribute managed by this class from
            a :class:`components.Member` instance. Defaults to

            .. code:: python

                lambda member: member[self.description]
        gendered_questions: Optional. Whether questions with tis attribute as hint should try to
            list only members with the same gender as the hint member. Defaults to :obj:`False`.
    """

    def __init__(
        self,
        description: str,
        questionable_attributes: List[Union[AttributeManager, str]],
        get_members_attribute: Callable[
            ['Member'], Optional[Union[AttributeType, List[AttributeType]]]
        ] = None,
        gendered_questions: bool = False,
    ) -> None:
        super().__init__(
            description=description,
            questionable_attributes=questionable_attributes,
            get_members_attribute=get_members_attribute,
            gendered_questions=gendered_questions,
        )
        self._cache_date: Optional[dtm.date] = None

    @property
    def data(self) -> MemberDict:
        today = dtm.date.today()
        if self._cache_date is None or today > self._cache_date:
            members: FrozenSet[Member] = frozenset(
                set().union(*self._data.values())  # type: ignore
            )
            self._data.clear()
            for member in members:
                attributes = self._gma_as_list(member)
                if attributes is None:
                    continue
                for attr in attributes:
                    self._data[attr].add(member)
            self._cache_date = today
        return self._data
