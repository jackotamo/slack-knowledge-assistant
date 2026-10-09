"""Source descriptions shared by terminal and browser interfaces."""
def describe_source(source):
    p = source.passage
    location = f"{p.location_kind} {p.start_line}-{p.end_line}"
    if p.page_number is not None:
        location = f"page {p.page_number}, {location}"
    return f"[{source.identifier}] {p.title} - {p.section}\n  {p.path}, {location}"
