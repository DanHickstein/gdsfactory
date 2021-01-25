from pp.component import Component
from pp.components.electrical.pad import pad
from pp.container import container
from pp.routing.connect_electrical import connect_electrical_shortest_path
from pp.types import ComponentOrFunction


@container
def add_electrical_pads_shortest(
    component: Component,
    pad: ComponentOrFunction = pad,
    pad_port_spacing: float = 50.0,
    **kwargs,
) -> Component:
    """add a pad to each closest electrical port

    Args:
        component:
        pad: pad element or function
        pad_port_spacing: between pad and port
        width: pad width
        height: pad height
        layer: pad layer

    """
    c = Component(f"{component.name}_e")
    ports = component.get_ports_list(port_type="dc")
    c << component

    pad = pad(**kwargs) if callable(pad) else pad
    pad_port_spacing += pad.settings["width"] / 2

    for port in ports:
        p = c << pad
        if port.orientation == 0:
            p.x = port.x + pad_port_spacing
            p.y = port.y
            c.add(connect_electrical_shortest_path(port, p.ports["W"]))
        elif port.orientation == 180:
            p.x = port.x - pad_port_spacing
            p.y = port.y
            c.add(connect_electrical_shortest_path(port, p.ports["E"]))
        elif port.orientation == 90:
            p.y = port.y + pad_port_spacing
            p.x = port.x
            c.add(connect_electrical_shortest_path(port, p.ports["S"]))
        elif port.orientation == 270:
            p.y = port.y - pad_port_spacing
            p.x = port.x
            c.add(connect_electrical_shortest_path(port, p.ports["N"]))

    c.ports = component.ports.copy()
    for port in ports:
        c.ports.pop(port.name)
    return c


if __name__ == "__main__":
    import pp

    c = pp.c.cross(length=100, layer=pp.LAYER.M3, port_type="dc")
    c = pp.c.mzi2x2(with_elec_connections=True)
    c = pp.c.wg_heater_connected()
    cc = add_electrical_pads_shortest(c)
    pp.show(cc)
