# Icon Library Standards

## Phosphor Icons Only

All icons in Aisy frontends must use **Phosphor Icons** with the `ph:` prefix.

**Do NOT use:**
- `mdi:` (Material Design Icons)
- `solar:` (Solar Icons)
- `eva:` (Eva Icons)
- `ic:` (Google Material Icons)
- `carbon:` (Carbon Icons)
- `material-symbols:` (Material Symbols)

**Always use:**
- `ph:` (Phosphor Icons)

## Common Icon Mappings

| Purpose | Use This (ph:) | NOT This |
|---------|----------------|----------|
| Bell/Notification | `ph:bell` | `mdi:bell-outline` |
| Chat/Comment | `ph:chat-circle` | `mdi:chat-outline` |
| Filter | `ph:funnel` | `mdi:filter-variant` |
| Search | `ph:magnifying-glass` | `mdi:magnify` |
| Clock/Time | `ph:clock` | `mdi:clock-alert-outline` |
| Shield | `ph:shield` | `mdi:shield-off-outline` |
| Web/Globe | `ph:globe` | `mdi:web` |
| Check | `ph:check` | `mdi:check` |
| Info | `ph:info` | `mdi:information-outline` |
| User/Account | `ph:user` | `mdi:account-plus-outline` |
| Arrow Up | `ph:arrow-up` | `mdi:arrow-up` |
| Expand | `ph:arrows-out` | `mdi:arrow-expand` |
| Dots Menu | `ph:dots-three` | `mdi:dots-horizontal` |
| Server | `ph:hard-drives` | `mdi:server-network` |
| Dropdown Arrow | `ph:caret-down` | `solar:alt-arrow-down-linear` |

## Usage Example

```jsx
// Correct
<Iconify icon="ph:bell" width={16} />

// Incorrect
<Iconify icon="mdi:bell-outline" width={16} />
```
