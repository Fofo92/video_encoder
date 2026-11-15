/* Follow menu buttons through libdvdnav's VM and report their title destinations. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <dvdnav/dvdnav.h>
#include <dvdnav/dvdnav_events.h>
#include <dvdread/ifo_read.h>

enum { MENU_LIMIT = 12, BLOCK_LIMIT = 100000 };

struct menu {
    dvdnav_t *nav;
    pci_t pci;
    int vts;
    int32_t pgc;
    int32_t program;
};

/* Return a positive title, zero for a menu, or -1 if playback cannot advance. */
static int advance(struct menu *state) {
    uint8_t block[2048];
    for (int step = 0; step < BLOCK_LIMIT; ++step) {
        int32_t title = 0, part = 0;
        if (dvdnav_is_domain_vts(state->nav) &&
            dvdnav_current_title_info(state->nav, &title, &part) == DVDNAV_STATUS_OK &&
            title > 0)
            return title;

        int32_t event, length;
        if (dvdnav_get_next_block(state->nav, block, &event, &length) != DVDNAV_STATUS_OK ||
            event == DVDNAV_STOP)
            return -1;

        if (event == DVDNAV_VTS_CHANGE) {
            dvdnav_vts_change_event_t change;
            if (length < (int32_t)sizeof(change))
                return -1;
            memcpy(&change, block, sizeof(change));
            state->vts = change.new_vtsN;
        } else if (event == DVDNAV_WAIT) {
            dvdnav_wait_skip(state->nav);
        } else if (event == DVDNAV_STILL_FRAME) {
            dvdnav_still_skip(state->nav);
        } else if (event == DVDNAV_NAV_PACKET) {
            pci_t *pci = dvdnav_get_current_nav_pci(state->nav);
            if (!pci || !(pci->hli.hl_gi.hli_ss & 3) || !pci->hli.hl_gi.btn_ns)
                continue;
            if (!dvdnav_is_domain_vmgm(state->nav) && !dvdnav_is_domain_vtsm(state->nav))
                continue;
            if (dvdnav_current_title_program(state->nav, &title, &state->pgc,
                                             &state->program) != DVDNAV_STATUS_OK)
                return -1;
            if (dvdnav_is_domain_vmgm(state->nav))
                state->vts = 0;
            state->pci = *pci;
            return 0;
        }
    }
    return -1;
}

/* A page may exist in several language units. Prefer the French unit selected
 * for playback and require a unique match otherwise. */
static int language_unit(dvd_reader_t *disc, const struct menu *menu) {
    if (menu->vts < 0 || menu->pgc < 1)
        return 0;
    ifo_handle_t *ifo = ifoOpen(disc, menu->vts);
    if (!ifo)
        return 0;
    int candidate = 0, count = 0;
    if (ifo->pgci_ut) {
        for (int i = 0; i < ifo->pgci_ut->nr_of_lus; ++i) {
            pgci_lu_t *unit = &ifo->pgci_ut->lu[i];
            if (!unit->pgcit || menu->pgc > unit->pgcit->nr_of_pgci_srp)
                continue;
            pgc_t *pgc = unit->pgcit->pgci_srp[menu->pgc - 1].pgc;
            if (!pgc || !pgc->cell_playback)
                continue;
            uint32_t sector = menu->pci.pci_gi.nv_pck_lbn;
            for (int j = 0; j < pgc->nr_of_cells; ++j) {
                const cell_playback_t *cell = &pgc->cell_playback[j];
                if (sector < cell->first_sector || sector > cell->last_sector)
                    continue;
                candidate = i + 1;
                ++count;
                if (unit->lang_code == 0x6672) {
                    ifoClose(ifo);
                    return candidate;
                }
                break;
            }
        }
    }
    ifoClose(ifo);
    return count == 1 ? candidate : 0;
}

static int seen(const struct menu *pages, int count, const struct menu *candidate) {
    for (int i = 0; i < count; ++i) {
        if (pages[i].vts == candidate->vts && pages[i].pgc == candidate->pgc &&
            pages[i].program == candidate->program)
            return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: dvd_menu_probe DVD\n");
        return 2;
    }
    struct menu pages[MENU_LIMIT] = {0};
    if (dvdnav_open(&pages[0].nav, argv[1]) != DVDNAV_STATUS_OK)
        return 1;
    dvd_reader_t *disc = DVDOpen(argv[1]);
    if (!disc) {
        dvdnav_close(pages[0].nav);
        return 1;
    }

    dvdnav_menu_language_select(pages[0].nav, "fr");
    int count = advance(&pages[0]) == 0 ? 1 : 0;
    for (int index = 0; index < count; ++index) {
        const struct menu *page = &pages[index];
        int unit = language_unit(disc, page);
        int buttons = page->pci.hli.hl_gi.btn_ns;
        if (buttons > 36)
            continue;
        for (int button = 1; button <= buttons; ++button) {
            struct menu branch = *page;
            if (dvdnav_dup(&branch.nav, page->nav) != DVDNAV_STATUS_OK)
                continue;
            if (dvdnav_button_select_and_activate(branch.nav, &branch.pci, button) != DVDNAV_STATUS_OK) {
                dvdnav_free_dup(branch.nav);
                continue;
            }
            int title = advance(&branch);
            if (title > 0 && unit && page->pci.hli.hl_gi.btngr_ns == 1) {
                const btni_t *b = &page->pci.hli.btnit[button - 1];
                printf("TITLE\t%d\t%d\t%d\t%d\t%d\t%d\t%u\t%u\t%u\t%u\n",
                       page->vts, unit, page->pgc, page->program, button, title,
                       b->x_start, b->y_start, b->x_end, b->y_end);
            }
            if (title == 0 && count < MENU_LIMIT && !seen(pages, count, &branch))
                pages[count++] = branch;
            else
                dvdnav_free_dup(branch.nav);
        }
    }
    for (int index = count - 1; index > 0; --index)
        dvdnav_free_dup(pages[index].nav);
    DVDClose(disc);
    dvdnav_close(pages[0].nav);
    return 0;
}
