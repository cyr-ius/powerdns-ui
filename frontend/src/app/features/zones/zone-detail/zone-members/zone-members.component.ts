import { Component, inject, signal } from "@angular/core";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../../core/services/pdns.service";
import { UserBasic, ZoneMember, ZoneRole } from "../../../../shared/models/pdns.model";
import { ZoneDetailStore } from "../zone-detail.store";

/** Members tab: users of the zone's account and their role. */
@Component({
  selector: "app-zone-members",
  imports: [TranslatePipe],
  templateUrl: "./zone-members.component.html",
  host: { class: "d-block" },
})
export class ZoneMembersComponent {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly zone = this.store.zone;
  readonly members = this.store.members;
  readonly isLoadingMembers = this.store.isLoadingMembers;
  readonly membersError = this.store.membersError;
  readonly membersSuccess = signal<string | null>(null);
  readonly newMemberUserId = signal<number | null>(null);
  readonly newMemberRole = signal<ZoneRole>("viewer");
  readonly isSavingMember = signal(false);

  availableUsersToAdd(): UserBasic[] {
    const memberIds = new Set(this.members().map((m) => m.user_id));
    return this.store.allUsers().filter((u) => !memberIds.has(u.id));
  }

  async addMember(): Promise<void> {
    const userId = this.newMemberUserId();
    if (!userId) return;
    this.isSavingMember.set(true);
    this.membersError.set(null);
    try {
      const member = await this.pdns.addZoneMember(this.store.zoneId, userId, this.newMemberRole());
      this.members.update((list) => [...list, member]);
      this.newMemberUserId.set(null);
      this.newMemberRole.set("viewer");
      this.flashMembersSuccess("Member added.");
    } catch {
      this.membersError.set("Error occurred while adding the member.");
    } finally {
      this.isSavingMember.set(false);
    }
  }

  async updateMemberRole(member: ZoneMember, role: ZoneRole): Promise<void> {
    try {
      const updated = await this.pdns.updateZoneMember(this.store.zoneId, member.user_id, role);
      this.members.update((list) => list.map((m) => (m.user_id === member.user_id ? updated : m)));
      this.flashMembersSuccess("Role updated.");
    } catch {
      this.membersError.set("Error occurred while updating the role.");
    }
  }

  async removeMember(member: ZoneMember): Promise<void> {
    if (!confirm(`Remove ${member.username} from this zone ?`)) return;
    try {
      await this.pdns.removeZoneMember(this.store.zoneId, member.user_id);
      this.members.update((list) => list.filter((m) => m.user_id !== member.user_id));
      this.flashMembersSuccess("Member removed.");
    } catch {
      this.membersError.set("Error occurred while removing the member.");
    }
  }

  private flashMembersSuccess(msg: string): void {
    this.membersSuccess.set(msg);
    setTimeout(() => this.membersSuccess.set(null), 3000);
  }
}
