import sys
from typing import List


class Relation:
    def __init__(self, name: str, variables: dict[str, str], private_keys: set[str]):
        self.name: str = name
        self.variables: dict[str, str] = variables
        self.private_keys: set[str] = private_keys
        self.last_variable: "VariableOrderNode | None" = None
        self.join_variables: set[str] = set()

    def var_type(self):
        s = ""
        for var in self.variables:
            s += f"\"{var}\": \"{self.variables[var]}\"\n"
        return s

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


def visualize_node(node, level: int = 0):
    # each level of the tree adds two spaces to the indentation
    print(" " * level * 4 + node.name)
    for child in node.children:
        # recursive call with increased indentation level
        visualize_node(child, level + 1)


def compute_descendants(node):
    for child in node.children:
        node.descendants.append(child)
        # add all descendants of the child to the current node's descendants
        node.descendants += compute_descendants(child)
    return node.descendants


class VariableOrderNode:
    def __init__(self, name: str, data_type: str = "int", all_non_join_below: bool = False):
        self.name: str = name
        self.children: "List[VariableOrderNode]" = []
        # add descendants attribute
        self.descendants: "List[VariableOrderNode]" = []
        self.parent: "VariableOrderNode | None" = None
        self.id = -1
        self.data_type = data_type
        self.all_non_join_below = all_non_join_below

    def add_child(self, child: "VariableOrderNode"):
        self.children.append(child)
        child.parent = self

    def descendants_variables(self):
        res: set[str] = set()
        for child in self.descendants:
            res.add(child.name)
        return res

    def child_variables(self):
        res: set[str] = set()
        for child in self.children:
            res.update(child.child_variables())
            res.add(child.name)
        return res

    def parent_variables(self):
        if self.parent is None:
            return set()
        return self.parent.parent_variables().union({self.parent.name})

    def parent_ids(self):
        if self.parent is None:
            return set()
        return self.parent.parent_ids().union({self.parent.id})

    def set_id(self, _id):
        self.id = _id
        next_id = _id + 1
        for child in self.children:
            next_id = child.set_id(next_id)
        return next_id

    def generate_config(self):
        res = f"{self.id} {self.name} {self.data_type} {self.parent.id if self.parent is not None else -1} {{{','.join([str(x) for x in self.parent_ids()])}}} 0\n"
        for child in self.children:
            res += child.generate_config()
        return res

    def generate_sql(self):

        (s, n) = self.generate_sql_line()

        if self.all_non_join_below:
            return s

        # remove duplicates in children based on name
        self.children = list({v.name: v for v in self.children}.values())
        vars = self.children

        # sort children by all_non_join_below with all_non_join_below = False first
        vars.sort(key=lambda x: x.all_non_join_below, reverse=True)

        for child in vars:
            s += child.generate_sql()

        return s

    def generate_sql_line(self):
        if self.all_non_join_below:

            # materialise all descendant in a list (there is only one path)
            descendants = [self]
            iterator = self
            while len(iterator.children) > 0:
                iterator = iterator.children[0]
                descendants.append(iterator)

            descendants_types = ",".join(
                [tpch_sql_type_table[x.name] for x in descendants])
            descendants_names = ",".join([x.name for x in descendants])
            # generate the SQL
            s = f"\t[lift<{self.id}>: RingFactorizedRelation<[{self.id}, {descendants_types}]>]({descendants_names}) *\n"
            return (s, len(descendants))

        else:
            s = f"\t[lift<{self.id}>: RingFactorizedRelation<[{self.id}, {tpch_sql_type_table[self.name]}]>]({self.name}) *\n"
            return (s, 1)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


Inventory = Relation("Inventory", {"locn": "int", "dateid": "int",
                     "ksn": "int", "inventoryunits": "int"}, {"locn", "dateid", "ksn"})
Location = Relation("Location",
                    {"locn": "int", "zip": "int", "rgn_cd": "int", "clim_zn_nbr": "int", "tot_area_sq_ft": "int",
                     "sell_area_sq_ft": "int", "avghhi": "int", "supertargetdistance": "double",
                     "supertargetdrivetime": "double", "targetdistance": "double", "targetdrivetime": "double",
                     "walmartdistance": "double", "walmartdrivetime": "double",
                     "walmartsupercenterdistance": "double", "walmartsupercenterdrivetime": "double"}, {"locn"})
Census = Relation("Census", {"zip": "int", "population": "int", "white": "int", "asian": "int", "pacific": "int",
                             "blackafrican": "int", "medianage": "double", "occupiedhouseunits": "int",
                             "houseunits": "int", "families": "int", "households": "int", "husbwife": "int",
                             "males": "int", "females": "int", "householdschildren": "int", "hispanic": "int"}, {"zip"})
Item = Relation("Item", {"ksn": "int", "subcategory": "int", "category": "int", "categoryCluster": "int",
                         "prize": "double"}, {"ksn"})
Weather = Relation("Weather", {"locn": "int", "dateid": "int", "rain": "int", "snow": "int", "maxtemp": "int",
                               "mintemp": "int", "meanwind": "double", "thunder": "int"}, {"locn", "dateid"})
Retailer_1_Q2 = Relation("q2", {"ksn": "int", "locn": "int", "dateid": "int",
                         "maxtemp": "int", "zip": "int", "rain": "int"}, {"ksn"})
Retailer_3_Q2 = Relation("R3q2", {"ksn": "int", "locn": "int", "dateid": "int",
                         "price": "double", "category": "int"}, {"ksn", "locn", "dateid"})


Part = Relation("part", {"partkey": "int", "p_name": "string", "p_mfgr": "string", "p_brand": "string", "p_type": "string",
                "p_size": "int", "p_container": "string", "p_retailprice": "double", "p_comment": "string"}, {"partkey"})
Supplier = Relation("supplier", {"suppkey": "int", "s_name": "string", "s_address": "string", "s_nationkey": "int",
                    "s_phone": "string", "s_acctbal": "double", "s_comment": "string"}, {"suppkey", "s_nationkey"})
PartSupp = Relation("partsupp", {"partkey": "int", "suppkey": "int", "ps_availqty": "int",
                    "ps_supplycost": "double", "ps_comment": "string"}, {"partkey", "suppkey"})
Customer = Relation("customer", {"custkey": "int", "c_name": "string", "c_address": "string", "nationkey": "int",
                    "c_phone": "string", "c_acctbal": "double", "c_mktsegment": "string", "c_comment": "string"}, {"custkey", "nationkey"})
Orders = Relation("orders", {"orderkey": "int", "custkey": "int", "o_orderstatus": "char", "o_totalprice": "double", "o_orderdate": "string",
                  "o_orderpriority": "string", "o_clerk": "string", "o_shippriority": "int", "o_comment": "string"}, {"orderkey"})
Lineitem = Relation("lineitem", {"orderkey": "int", "partkey": "int", "suppkey": "int", "l_linenumber": "int", "l_quantity": "double", "l_extendedprice": "double", "l_discount": "double", "l_tax": "double", "l_returnflag": "char",
                    "l_linestatus": "char", "l_shipdate": "string", "l_commitdate": "string", "l_receiptdate": "string", "l_shipinstruct": "string", "l_shipmode": "string", "l_comment": "string"}, {"orderkey", "partkey", "suppkey"})
Nation = Relation("nation", {"nationkey": "int", "n_name": "string",
                  "regionkey": "int", "n_comment": "string"}, {"nationkey"})
Region = Relation("region", {
                  "regionkey": "int", "r_name": "string", "r_comment": "string"}, {"regionkey"})
TPCH_1_Q2 = Relation("q2", {"orderkey": "int", "partkey": "int", "suppkey": "int",
                     "l_quantity": "double", "o_totalprice": "double"}, {"partkey", "suppkey"})


tpch_sql_type_table = {
    "custkey": "INT",
    "c_name": "VARCHAR(25)",
    "c_address": "VARCHAR(40)",
    "nationkey": "INT",
    "s_nationkey": "INT",
    "c_phone": "CHAR(15)",
    "c_acctbal": "DECIMAL",
    "c_mktsegment": "CHAR(10)",
    "c_comment": "VARCHAR(117)",
    "orderkey": "INT",
    "partkey": "INT",
    "suppkey": "INT",
    "l_linenumber": "INT",
    "l_quantity": "DECIMAL",
    "l_extendedprice": "DECIMAL",
    "l_discount": "DECIMAL",
    "l_tax": "DECIMAL",
    "l_returnflag": "CHAR(1)",
    "l_linestatus": "CHAR(1)",
    "l_shipdate": "CHAR(10)",
    "l_commitdate": "CHAR(10)",
    "l_receiptdate": "CHAR(10)",
    "l_shipinstruct": "CHAR(25)",
    "l_shipmode": "CHAR(10)",
    "l_comment": "VARCHAR(44)",
    "p_name": "VARCHAR(55)",
    "p_mfgr": "CHAR(25)",
    "p_brand": "CHAR(10)",
    "p_type": "VARCHAR(25)",
    "p_size": "INT",
    "p_container": "CHAR(10)",
    "p_retailprice": "DECIMAL",
    "p_comment": "VARCHAR(23)",
    "ps_availqty": "INT",
    "ps_supplycost": "DECIMAL",
    "ps_comment": "VARCHAR(199)",
    "s_name": "CHAR(25)",
    "s_address": "VARCHAR(40)",
    "s_phone": "CHAR(15)",
    "s_acctbal": "DECIMAL",
    "s_comment": "VARCHAR(101)",
    "o_custkey": "INT",
    "o_orderstatus": "CHAR(1)",
    "o_totalprice": "DECIMAL",
    "o_orderdate": "CHAR(10)",
    "o_orderpriority": "CHAR(15)",
    "o_clerk": "CHAR(15)",
    "o_shippriority": "INT",
    "o_comment": "VARCHAR(79)",
    "n_name": "CHAR(25)",
    "regionkey": "INT",
    "n_comment": "VARCHAR(152)",
    "r_name": "CHAR(25)",
    "r_comment": "VARCHAR(152)"
}


tpch_relations = [Part, Supplier, PartSupp,
                  Customer, Orders, Lineitem, Nation, Region]


def generate_txt(all_relations: "List[Relation]", root: "VariableOrderNode", free_variables: set[str]):
    for relation in all_relations:
        iterator = root
        while True:
            if set(iterator.child_variables()).isdisjoint(set(relation.variables.keys())):
                # append the free variables to iterator
                variables_to_add = set(relation.variables.keys()).difference(
                    iterator.parent_variables().union({iterator.name}))

                for variable in variables_to_add.intersection(free_variables):
                    new_node = VariableOrderNode(
                        variable, relation.variables[variable])
                    iterator.add_child(new_node)
                    iterator = new_node

                for variable in variables_to_add.difference(free_variables):
                    new_node = VariableOrderNode(
                        variable, relation.variables[variable])
                    iterator.add_child(new_node)
                    iterator = new_node
                relation.last_variable = iterator
                break
            else:
                for child in iterator.children:
                    if not (set(child.child_variables()).union({child.name})).isdisjoint(set(relation.variables.keys())):
                        iterator = child
                        break

    root.set_id(0)
    all_vars = set()
    for rel in all_relations:
        all_vars.update(rel.variables.keys())
    config_start = f"{len(all_vars)} {len(all_relations)}\n"
    config_file = config_start + root.generate_config()
    for relation in all_relations:
        config_file += f"{relation.name} {relation.last_variable.id} {','.join(relation.variables.keys())}\n"
    print(config_file)

    return config_file


def compute_join_variables(relations):
    join_vars = set(relations[0].variables.keys())
    for rel in relations:
        join_vars = join_vars.intersection(set(rel.variables.keys()))
    return join_vars


def generate_sql_text(all_relations: "List[Relation]", root: "VariableOrderNode", free_variables: set[str], query_group: str, q: str, path: str):

    # join_variables = compute_join_variables(all_relations)

    for relation in all_relations:
        iterator = root
        while True:
            if set(iterator.child_variables()).isdisjoint(set(relation.variables.keys())):
                # append the free variables to iterator
                variables_to_add = set(relation.variables.keys()).difference(
                    iterator.parent_variables().union({iterator.name}))

                for variable in variables_to_add.intersection(free_variables):
                    new_node = VariableOrderNode(
                        variable, relation.variables[variable])
                    iterator.add_child(new_node)
                    iterator = new_node
                    iterator.all_non_join_below = True
                relation.last_variable = iterator
                break
            else:
                for child in iterator.children:
                    if not (set(child.child_variables()).union({child.name})).isdisjoint(set(relation.variables.keys())):
                        iterator = child
                        break

    # visualize_node(root)

    s = f"IMPORT DTREE FROM FILE '{query_group}-{q}.txt';"
    s += "\n\n"

    s += "CREATE DISTRIBUTED TYPE RingFactorizedRelation\n"
    s += "FROM FILE 'ring/ring_factorized.hpp'\n"
    s += "WITH PARAMETER SCHEMA (dynamic_min);\n\n"

    for relation in all_relations:
        s += generate_relation_sql_text(relation, path)
        s += "\n"

    s += "\n"
    root.set_id(0)
    s += "SELECT SUM(\n"

    s += root.generate_sql()
    # remove the last *
    s = s[::-1].replace('*', "", 1)[::-1]
    s += ")\nFROM "
    s += " NATURAL JOIN ".join([rel.name for rel in all_relations])
    s += ";\n\n"

    print(s)

    return s


def generate_relation_sql_text(relation: "Relation", path: str):
    s = f"CREATE STREAM {relation.name} (\n"
    for key, value in relation.variables.items():
        s += f"\t{key} \t {tpch_sql_type_table[key]}, \n"
    s = s[:-3]
    s += f") \nFROM FILE './datasets/{path}/{relation.name}.csv' \nLINE DELIMITED CSV (delimiter := '|');\n"
    return s


def generate_retailer_all():
    root = VariableOrderNode("locn")
    dateid = VariableOrderNode("dateid")
    ksn = VariableOrderNode("ksn")
    zip = VariableOrderNode("zip")
    root.add_child(dateid)
    dateid.add_child(ksn)
    root.add_child(zip)
    relations = [Inventory, Location, Census, Item, Weather]
    free_vars = {"locn", "dateid", "ksn", "zip", "category", "snow"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_3():
    root = VariableOrderNode("ksn")
    relations = [Item, Inventory]
    free_vars = {"locn", "dateid", "ksn", "category", "price"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_4Q1a():
    root = VariableOrderNode("ksn")
    locn = VariableOrderNode("locn")
    root.add_child(locn)
    relations = [Item, Inventory, Location]
    free_vars = {"locn", "ksn", "category", "zip"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_4Q1b():
    ksn = VariableOrderNode("ksn")
    root = VariableOrderNode("locn")
    root.add_child(ksn)
    relations = [Item, Inventory, Location]
    free_vars = {"locn", "ksn", "category", "zip"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_4Q2():
    root = VariableOrderNode("ksn")
    relations = [Item, Inventory]
    free_vars = {"locn", "ksn", "category", "price"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_1Q1b():
    root = VariableOrderNode("ksn")
    locn = VariableOrderNode("locn")
    root.add_child(locn)
    dateid = VariableOrderNode("dateid")
    locn.add_child(dateid)
    relations = [Item, Inventory, Location, Weather]
    free_vars = {"locn", "ksn", "category", "price"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_1Q1c():
    root = VariableOrderNode("ksn")
    relations = [Item, Retailer_1_Q2]
    free_vars = {"locn", "ksn", "category", "dateid", "rain", "zip"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_retailer_3Q1c():
    root = VariableOrderNode("locn")
    dateid = VariableOrderNode("dateid")
    root.add_child(dateid)
    relations = [Retailer_3_Q2, Weather, Location]
    free_vars = {"locn", "dateid", "rain", "zip", "category", "ksn"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_3Q2():
    root = VariableOrderNode("suppkey")
    part = VariableOrderNode("partkey")
    root.add_child(part)
    relations = [Supplier, PartSupp, Lineitem]
    free_vars = {"suppkey", "partkey", "l_quantity",
                 "ps_availqty", "ps_supplycost", "s_name"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_1Q1b():
    root = VariableOrderNode("partkey")
    supp = VariableOrderNode("suppkey")
    order = VariableOrderNode("orderkey")
    root.add_child(supp)
    supp.add_child(order)
    relations = [Part, PartSupp, Lineitem, Orders]
    free_vars = {"orderkey", "suppkey", "partkey",
                 "l_quantity", "ps_availqty", "p_name", "o_totalprice"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_1Q1c():
    root = VariableOrderNode("partkey")
    supp = VariableOrderNode("suppkey")
    root.add_child(supp)
    relations = [Part, PartSupp, TPCH_1_Q2]
    free_vars = {"orderkey", "suppkey", "partkey",
                 "l_quantity", "ps_availqty", "p_name", "o_totalprice"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_4Q3():
    root = VariableOrderNode("custkey")
    relations = [Customer, Orders]
    free_vars = {"custkey", "orderkey", "nationkey"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_5_Q1():
    nation = VariableOrderNode("nationkey")
    part = VariableOrderNode("partkey")
    supp = VariableOrderNode("suppkey")
    supp.add_child(part)
    supp.add_child(nation)
    relations = [Nation, Supplier, Customer, Part, PartSupp]
    free_vars = {"nationkey", "partkey", "suppkey",
                 "n_name", "s_name", "p_name", "ps_availqty"}
    res = generate_txt(relations, supp, free_vars)
    return res


def generate_TPCH_5_Q2():
    nation = VariableOrderNode("nationkey")
    relations = [Nation, Supplier, Customer]
    free_vars = {"nationkey", "suppkey", "n_name",
                 "s_name", "s_address", "custkey"}
    res = generate_txt(relations, nation, free_vars)
    return res


def generate_TPCH_5_Q3():
    part = VariableOrderNode("partkey")
    relations = [Part, PartSupp]
    free_vars = {"partkey", "suppkey", "ps_availqty", "p_name"}
    res = generate_txt(relations, part, free_vars)
    return res


def generate_retailer_aggr_Q1():
    root = VariableOrderNode("ksn")
    relations = [Inventory]
    free_vars = {"ksn"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_3_Q3():
    root = VariableOrderNode("suppkey")
    relations = [Supplier, PartSupp]
    free_vars = {"suppkey", "ps_availqty", "ps_supplycost", "s_name"}
    res = generate_txt(relations, root, free_vars)
    return res


def generate_TPCH_7_Q1():
    root = VariableOrderNode("regionkey")
    relations = [Nation, Region]
    free_vars = {"regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment"}

    return (root, relations, free_vars)

    # res = generate_txt(relations, root, free_vars) if not sql else generate_sql_text(
    #     relations, root, free_vars, query_group, q, path)
    # return res


def generate_TPCH_7_Q2():
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    nation.add_child(region)

    relations = [Nation, Region, Customer]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment"}

    return (nation, relations, free_vars)

    # res = generate_txt(relations, nation, free_vars) if not sql else generate_sql_text(
    #     relations, nation, free_vars, query_group, q, path)
    # res += "\n"
    # return res


def generate_TPCH_7_Q3():
    root = VariableOrderNode("custkey")
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    root.add_child(nation)
    nation.add_child(region)

    relations = [Nation, Region, Customer, Orders]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment", "orderkey", "o_orderstatus"}

    return (root, relations, free_vars)


def generate_TPCH_7_Q4():
    root = VariableOrderNode("orderkey")
    custkey = VariableOrderNode("custkey")
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    root.add_child(custkey)
    custkey.add_child(nation)
    nation.add_child(region)

    relations = [Nation, Region, Customer, Orders, Lineitem]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment", "orderkey", "o_orderstatus", "partkey", "l_quantity", "suppkey"}

    return (root, relations, free_vars)


def generate_TPCH_7_Q5():
    partkey = VariableOrderNode("partkey")
    orderkey = VariableOrderNode("orderkey")
    custkey = VariableOrderNode("custkey")
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    orderkey.add_child(partkey)

    orderkey.add_child(custkey)
    custkey.add_child(nation)
    nation.add_child(region)

    relations = [Nation, Region, Customer, Orders, Lineitem, PartSupp, Part]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment", "orderkey", "o_orderstatus", "partkey", "l_quantity", "suppkey", "ps_avalqty", "p_name"}

    return (orderkey, relations, free_vars)


def generate_TPCH_7_Q6():
    partkey = VariableOrderNode("partkey")
    orderkey = VariableOrderNode("orderkey")
    custkey = VariableOrderNode("custkey")
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    orderkey.add_child(partkey)

    orderkey.add_child(custkey)
    custkey.add_child(nation)
    nation.add_child(region)

    relations = [Nation, Region, Customer, Orders, Lineitem, PartSupp, Part]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment", "orderkey", "o_orderstatus", "partkey", "l_quantity", "suppkey", "ps_avalqty", "p_name"}

    return (orderkey, relations, free_vars)


def generate_TPCH_7_Q7():
    suppkey = VariableOrderNode("suppkey")
    partkey = VariableOrderNode("partkey")
    orderkey = VariableOrderNode("orderkey")
    custkey = VariableOrderNode("custkey")
    nation = VariableOrderNode("nationkey")
    region = VariableOrderNode("regionkey")

    orderkey.add_child(partkey)
    partkey.add_child(suppkey)

    orderkey.add_child(custkey)
    custkey.add_child(nation)
    nation.add_child(region)

    relations = [Nation, Region, Customer, Orders,
                 Lineitem, PartSupp, Part, Supplier]
    free_vars = {"custkey", "c_name", "regionkey", "nationkey", "n_name",
                 "r_name", "r_comment", "n_comment", "orderkey", "o_orderstatus", "partkey", "l_quantity", "suppkey", "ps_avalqty", "p_name", "s_name"}

    return (orderkey, relations, free_vars)


# generate_retailer_4Q1a()
# generate_retailer_4Q1b()
# generate_retailer_4Q2()
# generate_retailer_1Q1b()
# generate_retailer_1Q1c()
# generate_retailer_3Q1c()
# generate_TPCH_3Q2()
# generate_TPCH_1Q1b()
# generate_TPCH_1Q1c()
# generate_TPCH_4Q3()
# generate_TPCH_5_Q1()
# generate_TPCH_5_Q2()
# generate_TPCH_5_Q3()
# generate_retailer_aggr_Q1()
# generate_TPCH_3_Q3()


# print("done")


def main(args):
    # big queries
    # generate_TPCH_7_Q1(True)

    # generate_TPCH_7_Q2(False)
    query_group = args[0]
    q = args[1]
    path = args[2]
    is_sql = args[3] == "sql"
    # if args has 5 elements, then we are redirecting the output to a file
    redirect = len(args) == 5

    root, relations, free_vars = None, None, None

    if q == "Q1":
        root, relations, free_vars = generate_TPCH_7_Q1()
    elif q == "Q2":
        root, relations, free_vars = generate_TPCH_7_Q2()
    elif q == "Q3":
        root, relations, free_vars = generate_TPCH_7_Q3()
    elif q == "Q4":
        root, relations, free_vars = generate_TPCH_7_Q4()
    elif q == "Q5":
        root, relations, free_vars = generate_TPCH_7_Q5()
    elif q == "Q6":
        root, relations, free_vars = generate_TPCH_7_Q6()
    elif q == "Q7":
        root, relations, free_vars = generate_TPCH_7_Q7()

    res = generate_txt(relations, root, free_vars) if not is_sql else generate_sql_text(
        relations, root, free_vars, query_group, q, path)
    res += "\n"

    if not redirect:
        visualize_node(root)

    return res


if __name__ == "__main__":
    # Pass the command-line arguments (excluding the script name) to the main function
    main(sys.argv[1:])
