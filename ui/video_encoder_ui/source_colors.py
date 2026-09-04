SOURCE_COLORS = (
    "#3daee9",
    "#e6a23c",
    "#67c23a",
)


def source_color(index):
    return SOURCE_COLORS[
        index % len(SOURCE_COLORS)
    ]
