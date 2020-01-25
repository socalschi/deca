from .vfs_db import VfsDatabase
from .ff_adf import AdfDatabase
from .hashes import hash32_func, hash48_func
from .ff_types import *


class DbWrap:
    def __init__(self, db: VfsDatabase, logger=None, index_offset=0):
        self._db = db
        self._adf_db = AdfDatabase()
        self._logger = logger
        self._index_offset = index_offset
        self._drop_results = False
        self._nodes_to_add = []
        self._nodes_to_update = set()
        self._string_hash_to_add = []

        self._adf_db.load_from_database(self._db)

    def log(self, msg):
        if self._logger is not None:
            self._logger.log(msg)

    def status(self, i, n):
        if self._logger is not None:
            self._logger.status(i, n)

    def index_offset_set(self, index_offset):
        self._index_offset = index_offset

    def file_obj_from(self, node, mode='rb'):
        return self._db.file_obj_from(node, mode)

    def node_where_uid(self, uid):
        return self._db.node_where_uid(uid)

    def nodes_where_hash32(self, hash32):
        return self._db.nodes_where_hash32(hash32)

    def hash_string_where_hash32_select_all(self, hash32):
        return self._db.hash_string_where_hash32_select_all(hash32)

    def hash_string_references_where_hs_rowid_select_all(self, rowid):
        return self._db.hash_string_references_where_hs_rowid_select_all(rowid)

    def game_info(self):
        return self._db.game_info

    def node_read_adf(self, node):
        return self._adf_db.read_node(self._db, node)

    def extract_types_from_exe(self, exe_path):
        return self._adf_db.extract_types_from_exe(exe_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and not self._drop_results:
            n_nodes_to_add = len(self._nodes_to_add)
            if n_nodes_to_add > 0:
                self.log('Determining file types: {} nodes'.format(len(self._nodes_to_add)))
                for ii, node in enumerate(self._nodes_to_add):
                    self.status(ii + self._index_offset, n_nodes_to_add + self._index_offset)
                    self._db.determine_ftype(node)

                self.status(n_nodes_to_add + self._index_offset, n_nodes_to_add + self._index_offset)

                self.log('DATABASE: Inserting {} nodes'.format(len(self._nodes_to_add)))
                self._db.node_add_many(self._nodes_to_add)

            if len(self._nodes_to_update) > 0:
                self.log('DATABASE: Updating {} nodes'.format(len(self._nodes_to_update)))
                self._db.node_update_many(self._nodes_to_update)

            hash_strings_to_add = list(set(self._string_hash_to_add))
            if len(hash_strings_to_add) > 0:
                self.log('DATABASE: Inserting {} hash strings'.format(len(hash_strings_to_add)))
                self._db.hash_string_add_many(hash_strings_to_add)

            self.log('DATABASE: Saving ADF Types')
            self._adf_db.save_to_database(self._db)

    def node_add(self, node):
        self._nodes_to_add.append(node)

    def node_update(self, node):
        self._nodes_to_update.add(node)

    def propose_string(
            self, string, parent_node=None, is_field_name=False, possible_file_types=None,
            used_at_runtime=None, fix_paths=True):
        p_types = 0

        if isinstance(string, str):
            string = string.encode('ascii', 'ignore')
        elif isinstance(string, bytes):
            try:
                string.decode('utf-8')
            except UnicodeDecodeError:
                # if logger is not None:
                #     logger.log('propose: BAD STRING NOT UTF-8 {}'.format(string))
                return None
        else:
            # if logger is not None:
            #     logger.log('propose: BAD STRING {}'.format(string))
            return None

        if fix_paths:
            string = string.replace(b'\\\\', b'/').replace(b'\\', b'/')

        p = None
        if parent_node is not None:
            p = parent_node.uid

        if possible_file_types is None:
            pass
        elif isinstance(possible_file_types, list):
            for pt in possible_file_types:
                p_types = p_types | ftype_list[pt]
        else:
            p_types = p_types | ftype_list[possible_file_types]

        h4 = hash32_func(string)
        h6 = hash48_func(string)
        rec = (h4, h6, string, p, is_field_name, used_at_runtime, p_types)

        self._string_hash_to_add.append(rec)

        return rec