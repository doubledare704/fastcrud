import pytest
from fastcrud import FastCRUD, JoinConfig
from tests.sqlalchemy.conftest import (
    Project,
    Participant,
    ProjectsParticipantsAssociation,
)


@pytest.mark.asyncio
async def test_many_to_many_nested_aggregates_and_counts_by_base(async_session):
    # Create base projects
    project1 = Project(id=1, name="Project 1", description="First Project")
    project2 = Project(id=2, name="Project 2", description="Second Project")

    # Create participants
    participant1 = Participant(id=1, name="Participant 1", role="Developer")
    participant2 = Participant(id=2, name="Participant 2", role="Designer")

    async_session.add_all([project1, project2, participant1, participant2])
    await async_session.commit()

    # Associations: project1 has 2 participants; project2 has 1
    links = [
        ProjectsParticipantsAssociation(project_id=1, participant_id=1),
        ProjectsParticipantsAssociation(project_id=1, participant_id=2),
        ProjectsParticipantsAssociation(project_id=2, participant_id=1),
    ]
    async_session.add_all(links)
    await async_session.commit()

    crud = FastCRUD(Project)

    joins_config = [
        JoinConfig(
            model=ProjectsParticipantsAssociation,
            join_on=Project.id == ProjectsParticipantsAssociation.project_id,
            join_type="inner",
            join_prefix="pp_",
        ),
        JoinConfig(
            model=Participant,
            join_on=ProjectsParticipantsAssociation.participant_id == Participant.id,
            join_type="inner",
            join_prefix="participant_",
            # Tell the nesting logic this should be aggregated under the base as a list
            relationship_type="one-to-many",
        ),
    ]

    result = await crud.get_multi_joined(
        db=async_session,
        joins_config=joins_config,
        nest_joins=True,
    )

    assert "data" in result
    data = result["data"]

    # Should aggregate by base primary key -> 2 base rows (one per project)
    assert len(data) == 2

    # total_count should reflect distinct base rows when nesting one-to-many
    assert result["total_count"] == 2

    proj1 = next(d for d in data if d["id"] == 1)
    proj2 = next(d for d in data if d["id"] == 2)

    # Participants should be nested as a list under key derived from join_prefix ("participant")
    assert "participant" in proj1 and isinstance(proj1["participant"], list)
    assert "participant" in proj2 and isinstance(proj2["participant"], list)

    # Project 1 has two participants; project 2 has one
    assert len(proj1["participant"]) == 2
    assert len(proj2["participant"]) == 1
