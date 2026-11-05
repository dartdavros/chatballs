"""Protected participant display shared by API and scenarios."""

from chatballs.identity.avatars import user_avatar_url_in


def member_payload(member):
    if member is None:
        return None
    return {
        "membershipId": member.pk,
        "userId": member.user_id,
        "name": member.user.full_name or member.user.email,
        "avatarUrl": user_avatar_url_in(member.user, member.organization_id),
    }

def participant_payload(participant):
    return {
        "id": participant.pk,
        "membershipId": participant.membership_id,
        "userId": participant.membership.user_id,
        "member": member_payload(participant.membership),
        "joinedBy": member_payload(participant.joined_by),
        "leftBy": member_payload(participant.left_by),
        "joinedByMembershipId": participant.joined_by_id,
        "joinedAt": participant.joined_at.isoformat(),
        "joinReason": participant.join_reason,
        "leftByMembershipId": participant.left_by_id,
        "leftAt": participant.left_at.isoformat() if participant.left_at else None,
        "leaveReason": participant.leave_reason,
    }
